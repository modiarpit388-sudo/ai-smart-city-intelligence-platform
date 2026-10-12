"""
Inference layer.  Turns the trained models into multi-step forecasts.

Multi-step strategy = *recursive forecasting*: the prediction for hour t+1 is fed back as the
"previous value" feature for hour t+2, and so on.  Weather for future hours comes from the
deterministic weather service, and the AQI / accident models consume the *traffic forecast*
- so the modules feed each other exactly like in a real smart-city stack.
"""
from datetime import datetime

import numpy as np
import pandas as pd

from ..extensions import db
from ..models import Prediction
from ..services.ingest import locations_df, read_sql
from ..simulation.weather import daily_weather, weather_frame
from ..utils import RISK_LEVELS, RISK_WEIGHTS, aqi_category, traffic_level
from . import pipelines as P
from .registry import active_model, load_bundle


class ModelNotReady(RuntimeError):
    pass


_cache: dict = {}


def clear_cache():
    _cache.clear()


def _cached(key, fn):
    k = (key, datetime.now().strftime("%Y%m%d%H"))
    if k not in _cache:
        _cache[k] = fn()
    return _cache[k]


def _bundle(module):
    b = load_bundle(module)
    if b is None:
        raise ModelNotReady(f"Model '{module}' has not been trained yet")
    return b


def areas() -> pd.DataFrame:
    return locations_df().rename(columns={"id": "area_id"}).reset_index(drop=True)


def _persist(module, area_ids, times, values, labels=None):
    """Store the newest forecast snapshot in the `predictions` table."""
    try:
        m = active_model(module)
        Prediction.query.filter_by(module=module).delete()
        rows = []
        for i, a in enumerate(area_ids):
            for j, t in enumerate(times):
                rows.append({"module": module, "location_id": int(a) if a is not None else None,
                             "target_time": pd.Timestamp(t).to_pydatetime(), "value": float(values[i][j]),
                             "label": labels[i][j] if labels is not None else None,
                             "model_id": m.id if m else None, "created_at": datetime.now()})
        db.session.execute(Prediction.__table__.insert(), rows)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _latest(table, cols, ts_col="timestamp", key="location_id") -> pd.DataFrame:
    sql = (f"SELECT t.{key} AS area_id, t.{ts_col} AS ts, {', '.join('t.' + c for c in cols)} FROM {table} t "
           f"JOIN (SELECT {key} AS k, MAX({ts_col}) AS mx FROM {table} GROUP BY {key}) m "
           f"ON t.{key} = m.k AND t.{ts_col} = m.mx ORDER BY t.{key}")
    df = read_sql(sql)
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def latest_traffic():
    return _latest("traffic_data", ["traffic_index", "avg_speed", "vehicle_count", "weather", "rain_mm", "temperature"])


def latest_aqi():
    return _latest("air_quality", ["aqi", "pm25", "pm10", "co", "no2", "so2", "o3", "temperature", "humidity",
                                   "wind_speed", "rain_mm", "traffic_index"])


def latest_accident():
    return _latest("accident_data", ["traffic_index", "road_code", "has_junction", "rain_mm", "visibility_km",
                                     "avg_speed", "is_night", "hist_accidents", "risk_score", "risk_level"])


# ============================================================================ TRAFFIC
def traffic_forecast(hours: int = 48) -> dict:
    return _cached(("traffic", hours), lambda: _traffic_forecast(hours))


def _traffic_forecast(hours):
    model = _bundle("traffic")["model"]
    A = areas()
    last = latest_traffic().set_index("area_id").reindex(A["area_id"])
    t0 = last["ts"].max()
    times = pd.date_range(t0 + pd.Timedelta(hours=1), periods=hours, freq="h")
    w = weather_frame(times)
    prev = last["traffic_index"].values.astype(float)
    out = np.zeros((len(A), hours))
    base = A[["area_id", "traffic_base", "road_code", "has_junction", "commercial_index"]]
    for h in range(hours):
        df = base.copy()
        df["timestamp"], df["rain_mm"], df["temperature"], df["prev_index"] = times[h], w.rain_mm.iloc[h], w.temperature.iloc[h], prev
        pred = np.clip(model.predict(P.traffic_features(df)), 3, 100)
        out[:, h], prev = pred, pred
    res = {"area_ids": A["area_id"].tolist(), "times": times, "values": out, "now": last["traffic_index"].values}
    _persist("traffic", res["area_ids"], times[:12], out[:, :12], [[traffic_level(v) for v in r[:12]] for r in out])
    return res


# ============================================================================ AIR QUALITY
def aqi_forecast(hours: int = 48) -> dict:
    return _cached(("aqi", hours), lambda: _aqi_forecast(hours))


def _aqi_forecast(hours):
    model = _bundle("aqi")["model"]
    A = areas()
    tf = traffic_forecast(max(hours, 48))
    last = latest_aqi().set_index("area_id").reindex(A["area_id"])
    t0 = last["ts"].max()
    times = pd.date_range(t0 + pd.Timedelta(hours=1), periods=hours, freq="h")
    w = weather_frame(times)
    prev = last["aqi"].values.astype(float)
    out = np.zeros((len(A), hours))
    base = A[["area_id", "pollution_base", "industrial_index"]]
    for h in range(hours):
        df = base.copy()
        df["timestamp"], df["temperature"], df["humidity"] = times[h], w.temperature.iloc[h], w.humidity.iloc[h]
        df["wind_speed"], df["rain_mm"] = w.wind_speed.iloc[h], w.rain_mm.iloc[h]
        df["traffic_index"], df["aqi_prev"] = tf["values"][:, h], prev
        pred = np.clip(model.predict(P.aqi_features(df)), 15, 500)
        out[:, h], prev = pred, pred
    res = {"area_ids": A["area_id"].tolist(), "times": times, "values": np.round(out), "now": last["aqi"].values}
    _persist("aqi", res["area_ids"], times[:24], res["values"][:, :24], [[aqi_category(v) for v in r[:24]] for r in res["values"]])
    return res


# ============================================================================ ACCIDENT RISK
def estimate_speed(traffic_index, road_code):
    free = np.array([38, 48, 60, 32])[np.asarray(road_code, dtype=int)]
    return np.clip(free * (1 - np.asarray(traffic_index) / 115) ** 1.1, 4, 70)


def accident_predict(features: pd.DataFrame):
    """features must already be shaped by P.accident_features. Returns (risk_pct, level_idx, proba)."""
    b = _bundle("accident")
    proba = b["model"].predict_proba(features)
    risk = (proba * RISK_WEIGHTS[None, :]).sum(axis=1) * 100
    return np.round(risk, 1), proba.argmax(axis=1), proba


def accident_forecast(hours: int = 12) -> dict:
    return _cached(("accident", hours), lambda: _accident_forecast(hours))


def _accident_forecast(hours):
    A = areas()
    tf = traffic_forecast(max(hours, 48))
    times = tf["times"][:hours]
    w = weather_frame(times)
    frames = []
    for h in range(hours):
        idx = tf["values"][:, h]
        hr = times[h].hour
        frames.append(pd.DataFrame({
            "timestamp": times[h], "traffic_index": idx, "road_code": A["road_code"].values,
            "has_junction": A["has_junction"].values, "rain_mm": w.rain_mm.iloc[h],
            "visibility_km": w.visibility_km.iloc[h], "avg_speed": estimate_speed(idx, A["road_code"].values),
            "is_night": int(hr >= 19 or hr < 6), "hist_accidents": A["accident_hist"].values}))
    big = pd.concat(frames, ignore_index=True)
    risk, lvl, proba = accident_predict(P.accident_features(big))
    n = len(A)
    risk = risk.reshape(hours, n).T
    lvl = lvl.reshape(hours, n).T
    res = {"area_ids": A["area_id"].tolist(), "times": times, "risk": risk, "level_idx": lvl, "features": big}
    _persist("accident", res["area_ids"], times, risk, [[RISK_LEVELS[i] for i in r] for r in lvl])
    return res


def accident_now() -> pd.DataFrame:
    """Risk for the current hour, computed from the newest sensor row of every area."""
    return _cached(("accident_now",), _accident_now)


def _accident_now():
    last = latest_accident()
    feats = last.rename(columns={"ts": "timestamp"})
    risk, lvl, _ = accident_predict(P.accident_features(feats))
    last["risk_pct"] = risk
    last["level"] = [RISK_LEVELS[i] for i in lvl]
    return last


def accident_factors(row: dict) -> list:
    """Human-readable 'main factors' behind a risk prediction."""
    f = []
    if row["traffic_index"] >= 70:
        f.append((row["traffic_index"] / 100 * 0.30, "Heavy traffic"))
    if row["rain_mm"] >= 0.5:
        f.append((min(row["rain_mm"], 10) / 10 * 0.15 + 0.05, "Rain"))
    if row["visibility_km"] < 6:
        f.append(((1 - row["visibility_km"] / 10) * 0.15, "Low visibility"))
    if row["is_night"]:
        f.append((0.15, "Night-time"))
    if row["hist_accidents"] >= 30:
        f.append((row["hist_accidents"] / 50 * 0.15, "High historical accident count"))
    if row["has_junction"]:
        f.append((0.10, "Busy junction / intersection"))
    if row["avg_speed"] > 50:
        f.append((0.08, "High vehicle speed"))
    f.sort(key=lambda t: -t[0])
    return [t[1] for t in f[:4]] or ["No major risk factors"]


# ============================================================================ ELECTRICITY
def electricity_forecast(hours: int = 48) -> dict:
    return _cached(("elec", hours), lambda: _electricity_forecast(hours))


def _electricity_forecast(hours):
    model = _bundle("electricity")["model"]
    hist = read_sql("SELECT timestamp, demand_mw, temperature, humidity FROM electricity_data ORDER BY timestamp DESC LIMIT 48")
    hist["timestamp"] = pd.to_datetime(hist["timestamp"])
    hist = hist.sort_values("timestamp").reset_index(drop=True)
    series = list(hist["demand_mw"].values.astype(float))
    t0 = hist["timestamp"].iloc[-1]
    times = pd.date_range(t0 + pd.Timedelta(hours=1), periods=hours, freq="h")
    w = weather_frame(times)
    out = []
    for h in range(hours):
        df = pd.DataFrame({"timestamp": [times[h]], "temperature": [w.temperature.iloc[h]],
                           "humidity": [w.humidity.iloc[h]], "lag1": [series[-1]], "lag24": [series[-24]]})
        p = float(model.predict(P.elec_features(df))[0])
        series.append(p)
        out.append(p)
    res = {"times": times, "values": np.round(out, 1), "history": hist}
    _persist("electricity", [None], times[:24], [res["values"][:24]])
    return res


# ============================================================================ WATER / WASTE (daily)
def _daily_series(table, col, days=14):
    mx = read_sql(f"SELECT MAX(date) AS d FROM {table}")["d"].iloc[0]
    cut = (pd.Timestamp(mx) - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    df = read_sql(f"SELECT date, location_id AS area_id, {col} FROM {table} WHERE date > :cut", {"cut": cut})
    df["date"] = pd.to_datetime(df["date"])
    pv = df.pivot(index="area_id", columns="date", values=col).sort_index(axis=1)
    return pv


def water_forecast(days: int = 7) -> dict:
    return _cached(("water", days), lambda: _daily_forecast("water", "water_consumption", "consumption_ml", days,
                                                            P.water_features, ["area_id", "population_k", "type_code"]))


def waste_forecast(days: int = 7) -> dict:
    return _cached(("waste", days), lambda: _daily_forecast("waste", "waste_data", "total_tons", days,
                                                            P.waste_features, ["area_id", "population_k", "commercial_index"]))


def _daily_forecast(module, table, col, days, feat_fn, static_cols):
    model = _bundle(module)["model"]
    A = areas()
    pv = _daily_series(table, col, 14).reindex(A["area_id"])
    series = pv.values.astype(float)
    d0 = pv.columns.max()
    dates = pd.date_range(d0 + pd.Timedelta(days=1), periods=days, freq="D")
    dw = daily_weather(dates)
    base = A[static_cols]
    out = np.zeros((len(A), days))
    for d in range(days):
        df = base.copy()
        df["date"], df["temp_max"], df["rain_mm"] = dates[d], dw.temp_max.iloc[d], dw.rain_mm.iloc[d]
        df["prev_day"], df["prev_week"] = series[:, -1], series[:, -7]
        pred = np.clip(model.predict(feat_fn(df)), 0.05, None)
        out[:, d] = pred
        series = np.hstack([series, pred[:, None]])
    res = {"area_ids": A["area_id"].tolist(), "dates": dates, "values": np.round(out, 3),
           "history": pv, "today": pv.iloc[:, -1].values}
    _persist(module, res["area_ids"], dates, res["values"])
    return res
