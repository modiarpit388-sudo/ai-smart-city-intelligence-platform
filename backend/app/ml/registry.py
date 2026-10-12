"""
Model registry / training harness shared by every ML module.

For each module we
  1. train several candidate algorithms on a time-based split (oldest data -> train, newest -> test)
  2. evaluate them (RMSE/MAE/R2 or Accuracy/Precision/Recall/F1)
  3. re-fit the best one on ALL data and save it with joblib
  4. write every candidate + its metrics to the `ml_models` / `model_metrics` tables
     so that the admin dashboard can show and compare them.
"""
import json
import os
import time
import warnings

import joblib
import numpy as np
from flask import current_app
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..extensions import db
from ..models import MLModel, ModelMetric

warnings.filterwarnings("ignore")

try:  # XGBoost is optional – the platform works without it
    from xgboost import XGBClassifier, XGBRegressor
    HAS_XGB = True
except Exception:  # pragma: no cover
    HAS_XGB = False

_CACHE: dict = {}

MODULES = {
    "traffic": "Traffic Prediction", "accident": "Accident Risk", "aqi": "Air Quality",
    "electricity": "Electricity Demand", "water": "Water Consumption", "waste": "Waste Generation",
    "complaint_category": "Complaint Category (NLP)", "complaint_priority": "Complaint Priority (NLP)",
    "complaint_cluster": "Complaint Grouping (K-Means)",
}


# ------------------------------------------------------------------------- candidates
def regression_candidates() -> dict:
    c = {
        "Linear Regression": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "Random Forest": RandomForestRegressor(n_estimators=70, max_depth=14, min_samples_leaf=3, n_jobs=-1, random_state=42),
        "Gradient Boosting": HistGradientBoostingRegressor(max_iter=220, learning_rate=0.08, random_state=42),
    }
    if HAS_XGB:
        c["XGBoost"] = XGBRegressor(n_estimators=260, learning_rate=0.06, max_depth=6, subsample=0.9,
                                    colsample_bytree=0.9, n_jobs=-1, random_state=42, verbosity=0)
    return c


def classification_candidates() -> dict:
    c = {
        "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)),
        "Random Forest": RandomForestClassifier(n_estimators=90, max_depth=14, min_samples_leaf=3, n_jobs=-1, random_state=42),
        "Gradient Boosting": HistGradientBoostingClassifier(max_iter=180, learning_rate=0.08, random_state=42),
    }
    if HAS_XGB:
        c["XGBoost"] = XGBClassifier(n_estimators=200, learning_rate=0.08, max_depth=5, subsample=0.9,
                                     n_jobs=-1, random_state=42, verbosity=0)
    return c


# ------------------------------------------------------------------------- persistence
def _path(module: str) -> str:
    os.makedirs(current_app.config["MODEL_DIR"], exist_ok=True)
    return os.path.join(current_app.config["MODEL_DIR"], f"{module}.joblib")


def save_bundle(module: str, bundle: dict):
    joblib.dump(bundle, _path(module))
    _CACHE[module] = bundle


def load_bundle(module: str):
    if module in _CACHE:
        return _CACHE[module]
    p = _path(module)
    if not os.path.exists(p):
        return None
    _CACHE[module] = joblib.load(p)
    return _CACHE[module]


def clear_model_cache():
    _CACHE.clear()


def is_trained(module: str) -> bool:
    return os.path.exists(_path(module)) and MLModel.query.filter_by(module=module, is_active=True).first() is not None


def active_model(module: str):
    return MLModel.query.filter_by(module=module, is_active=True).first()


def model_summary(module: str) -> dict:
    m = active_model(module)
    if not m:
        return {"module": module, "trained": False}
    return {"module": module, "trained": True, "algorithm": m.algorithm, "version": m.version,
            "trained_at": m.trained_at.isoformat(), "metrics": {x.name: round(x.value, 4) for x in m.metrics}}


# ------------------------------------------------------------------------- metrics
def regression_metrics(y, p) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y, p)))
    return {"RMSE": rmse, "MAE": float(mean_absolute_error(y, p)), "R2": float(r2_score(y, p))}


def classification_metrics(y, p) -> dict:
    return {
        "Accuracy": float(accuracy_score(y, p)),
        "Precision": float(precision_score(y, p, average="weighted", zero_division=0)),
        "Recall": float(recall_score(y, p, average="weighted", zero_division=0)),
        "F1": float(f1_score(y, p, average="weighted", zero_division=0)),
    }


def _importance(model, X_test, y_test, cols, scoring):
    """Model-agnostic permutation importance on (at most) 1500 test rows."""
    try:
        n = min(1500, len(X_test))
        idx = np.random.RandomState(0).choice(len(X_test), n, replace=False)
        r = permutation_importance(model, X_test.iloc[idx], np.asarray(y_test)[idx], n_repeats=3,
                                   random_state=0, scoring=scoring, n_jobs=1)
        imp = np.clip(r.importances_mean, 0, None)
        tot = imp.sum() or 1.0
        return {c: float(round(v / tot, 4)) for c, v in sorted(zip(cols, imp), key=lambda t: -t[1])}
    except Exception:
        return {}


def _next_version(module: str) -> int:
    last = db.session.query(db.func.max(MLModel.version)).filter_by(module=module).scalar()
    return (last or 0) + 1


def _store(module, task, results, best, X_cols, n_train, n_test, importance, sample, seconds):
    """Write all candidate rows; only `best` is flagged active."""
    version = _next_version(module)
    MLModel.query.filter_by(module=module, is_active=True).update({"is_active": False})
    for name, r in results.items():
        row = MLModel(module=module, algorithm=name, task=task, version=version, is_active=(name == best),
                      train_rows=n_train, test_rows=n_test, train_seconds=round(r["seconds"], 2),
                      features=json.dumps(list(X_cols)),
                      feature_importance=json.dumps(importance) if name == best else None,
                      sample=json.dumps(sample) if name == best else None)
        db.session.add(row)
        db.session.flush()
        for k, v in r["metrics"].items():
            db.session.add(ModelMetric(model_id=row.id, name=k, value=float(v)))
    # keep only the 3 most recent versions to avoid unbounded growth
    old = MLModel.query.filter(MLModel.module == module, MLModel.version < version - 2).all()
    for o in old:
        db.session.delete(o)
    db.session.commit()
    return version


# ------------------------------------------------------------------------- training entry points
def train_regression(module, X, y, test_mask, extra_bundle=None, sample_x=None, log=print):
    """X: DataFrame, y: Series, test_mask: boolean array marking the (latest) test rows."""
    t0 = time.time()
    Xtr, Xte, ytr, yte = X[~test_mask], X[test_mask], y[~test_mask], y[test_mask]
    results, fitted = {}, {}
    for name, est in regression_candidates().items():
        s = time.time()
        m = clone(est).fit(Xtr, ytr)
        pred = m.predict(Xte)
        results[name] = {"metrics": regression_metrics(yte, pred), "seconds": time.time() - s}
        fitted[name] = (m, pred)
        log(f"      · {name:<18} RMSE={results[name]['metrics']['RMSE']:.3f}  R2={results[name]['metrics']['R2']:.3f}")
    best = min(results, key=lambda k: results[k]["metrics"]["RMSE"])
    bm, bpred = fitted[best]
    importance = _importance(bm, Xte, yte, X.columns, "neg_root_mean_squared_error")
    # actual-vs-predicted sample for the admin chart
    step = max(1, len(yte) // 120)
    sample = {"actual": [round(float(v), 2) for v in np.asarray(yte)[::step][:120]],
              "predicted": [round(float(v), 2) for v in bpred[::step][:120]]}
    final = clone(regression_candidates()[best]).fit(X, y)  # refit on all data for deployment
    bundle = {"model": final, "features": list(X.columns), "algorithm": best, "task": "regression"}
    bundle.update(extra_bundle or {})
    save_bundle(module, bundle)
    _store(module, "regression", results, best, X.columns, len(Xtr), len(Xte), importance, sample, time.time() - t0)
    log(f"   ✔ {module}: best = {best}")
    return best, results


def train_classification(module, X, y, test_mask, classes, extra_bundle=None, log=print):
    t0 = time.time()
    y = np.asarray(y)
    cls_to_i = {c: i for i, c in enumerate(classes)}
    yi = np.array([cls_to_i[v] for v in y])
    Xtr, Xte, ytr, yte = X[~test_mask], X[test_mask], yi[~test_mask], yi[test_mask]
    results, fitted = {}, {}
    for name, est in classification_candidates().items():
        s = time.time()
        m = clone(est).fit(Xtr, ytr)
        pred = m.predict(Xte)
        results[name] = {"metrics": classification_metrics(yte, pred), "seconds": time.time() - s}
        fitted[name] = (m, pred)
        log(f"      · {name:<20} acc={results[name]['metrics']['Accuracy']:.3f}  F1={results[name]['metrics']['F1']:.3f}")
    best = max(results, key=lambda k: results[k]["metrics"]["F1"])
    bm, bpred = fitted[best]
    importance = _importance(bm, Xte, yte, X.columns, "f1_weighted")
    cm = confusion_matrix(yte, bpred, labels=list(range(len(classes)))).tolist()
    sample = {"classes": list(classes), "confusion_matrix": cm}
    final = clone(classification_candidates()[best]).fit(X, yi)
    bundle = {"model": final, "features": list(X.columns), "algorithm": best, "task": "classification", "classes": list(classes)}
    bundle.update(extra_bundle or {})
    save_bundle(module, bundle)
    _store(module, "classification", results, best, X.columns, len(Xtr), len(Xte), importance, sample, time.time() - t0)
    log(f"   ✔ {module}: best = {best}")
    return best, results


def latest_test_mask(timestamps, days: int):
    """Boolean mask selecting the most recent `days` days (time-based split)."""
    ts = np.asarray(timestamps, dtype="datetime64[ns]")
    cutoff = ts.max() - np.timedelta64(days, "D")
    return ts > cutoff
