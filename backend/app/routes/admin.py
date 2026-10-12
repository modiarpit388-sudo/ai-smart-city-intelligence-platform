"""Admin: user management, dataset management, ML model management, system analytics."""
import io
import json

import pandas as pd
from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import func

from ..auth import auth_required
from ..extensions import db
from ..ml import trainer
from ..ml.registry import MODULES
from ..models import (Alert, Complaint, Department, MLModel, Notification, User)
from ..services.ingest import TABLES, dataset_summary, ensure_data_current, insert_df

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ------------------------------------------------------------------ users
@bp.get("/users")
@auth_required("admin")
def users():
    return jsonify(users=[u.to_dict() for u in User.query.order_by(User.role, User.name).all()],
                   departments=[d.to_dict() for d in Department.query.all()])


@bp.post("/users")
@auth_required("admin")
def create_user():
    d = request.get_json(force=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not email or not d.get("name") or len(d.get("password") or "") < 6:
        return jsonify(error="Name, email and a password of 6+ characters are required"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="Email already exists"), 409
    role = d.get("role", "authority")
    if role not in ("citizen", "authority", "admin"):
        return jsonify(error="Invalid role"), 400
    u = User(name=d["name"], email=email, role=role, department_id=d.get("department_id") if role == "authority" else None,
             area_id=d.get("area_id"))
    u.set_password(d["password"])
    db.session.add(u)
    db.session.commit()
    return jsonify(user=u.to_dict()), 201


@bp.put("/users/<int:uid>")
@auth_required("admin")
def update_user(uid):
    u = User.query.get_or_404(uid)
    d = request.get_json(force=True) or {}
    if u.id == g.user.id and d.get("is_active") is False:
        return jsonify(error="You cannot deactivate your own account"), 400
    for f in ("name", "role", "department_id", "area_id", "is_active"):
        if f in d:
            setattr(u, f, d[f])
    if d.get("password"):
        u.set_password(d["password"])
    db.session.commit()
    return jsonify(user=u.to_dict())


# ------------------------------------------------------------------ datasets
@bp.get("/datasets")
@auth_required("admin")
def datasets():
    return jsonify(datasets=dataset_summary())


@bp.post("/datasets/ingest")
@auth_required("admin")
def ingest():
    return jsonify(added=ensure_data_current())


@bp.get("/datasets/<table>/export")
@auth_required("admin")
def export(table):
    if table not in TABLES:
        return jsonify(error="Unknown table"), 404
    limit = request.args.get("limit", 50000, type=int)
    df = pd.read_sql(f"SELECT * FROM {table} ORDER BY id DESC LIMIT {int(limit)}", db.engine)
    return Response(df.to_csv(index=False), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={table}.csv"})


@bp.post("/datasets/<table>/import")
@auth_required("admin")
def import_csv(table):
    if table not in TABLES:
        return jsonify(error="Unknown table"), 404
    f = request.files.get("file")
    if not f:
        return jsonify(error="Attach a CSV file (field name: file)"), 400
    model = TABLES[table]
    df = pd.read_csv(io.BytesIO(f.read()))
    cols = [c.name for c in model.__table__.columns if c.name != "id"]
    unknown = [c for c in df.columns if c not in cols and c != "id"]
    if unknown:
        return jsonify(error=f"Unknown columns: {', '.join(unknown)}. Expected: {', '.join(cols)}"), 400
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.drop(columns=["id"], errors="ignore").astype(object).where(df.notna(), None)
    n = insert_df(model, df)
    from ..ml.forecast import clear_cache
    clear_cache()
    return jsonify(imported=n)


# ------------------------------------------------------------------ ML models
@bp.get("/models")
@auth_required("admin")
def models():
    out = []
    for key, title in MODULES.items():
        active = MLModel.query.filter_by(module=key, is_active=True).first()
        if not active:
            out.append({"module": key, "title": title, "trained": False})
            continue
        cands = MLModel.query.filter_by(module=key, version=active.version).all()
        out.append({
            "module": key, "title": title, "trained": True, "task": active.task, "version": active.version,
            "algorithm": active.algorithm, "trained_at": active.trained_at.isoformat(), "train_rows": active.train_rows,
            "test_rows": active.test_rows, "features": json.loads(active.features or "[]"),
            "importance": json.loads(active.feature_importance or "{}"), "sample": json.loads(active.sample or "{}"),
            "metrics": {m.name: round(m.value, 4) for m in active.metrics},
            "candidates": [{"algorithm": c.algorithm, "active": c.is_active, "seconds": c.train_seconds,
                            "metrics": {m.name: round(m.value, 4) for m in c.metrics}} for c in cands],
        })
    return jsonify(models=out, status=trainer.STATUS)


@bp.post("/models/retrain")
@auth_required("admin")
def retrain():
    groups = (request.get_json(silent=True) or {}).get("groups") or trainer.ALL_GROUPS
    bad = [g_ for g_ in groups if g_ not in trainer.ALL_GROUPS]
    if bad:
        return jsonify(error=f"Unknown module(s): {bad}"), 400
    from flask import current_app
    ok = trainer.start_background(current_app._get_current_object(), groups)
    if not ok:
        return jsonify(error="A training job is already running"), 409
    return jsonify(started=True, groups=groups)


@bp.get("/models/status")
@auth_required("admin")
def train_status():
    return jsonify(trainer.STATUS)


# ------------------------------------------------------------------ analytics
@bp.get("/analytics")
@auth_required("admin")
def analytics():
    role_counts = dict(db.session.query(User.role, func.count(User.id)).group_by(User.role).all())
    st = dict(db.session.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all())
    return jsonify(users=role_counts, complaints=st, alerts_active=Alert.query.filter_by(is_active=True).count(),
                   notifications=Notification.query.count(), datasets=dataset_summary(),
                   models_trained=MLModel.query.filter_by(is_active=True).count())
