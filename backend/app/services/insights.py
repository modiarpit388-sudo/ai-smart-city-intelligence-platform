"""
Insights layer: combines live database readings with model forecasts into the JSON payloads
consumed by the React dashboards.  All numbers shown in the UI come from here – nothing is invented.
"""
import math

import numpy as np
import pandas as pd

from ..extensions import db
from ..ml import forecast as F
from ..ml import pipelines as P
from ..ml.registry import active_model, model_summary
from ..models import Alert, Complaint
from ..services.ingest import read_sql
from ..utils import RISK_LEVELS, aqi_category, iso, pct_change, traffic_level, sub_indices


# ----------------------------------------------------------------------------- helpers
def hlabel(ts) -> str:
    h = pd.Timestamp(ts).hour
    return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"


def _f(x, nd=1):
    return round(float(x), nd)


def status_from_ratio(r, hi=1.08, lo=0.92):
    return "HIGH" if r > hi else "LOW" if r < lo else "NORMAL"


def _area_row(area_id):
    A = F.areas()
    r = A[A["area_id"] == int(area_id)]
    if r.empty:
        raise KeyError("area not found")
    return r.iloc[0]


def _pos(area_id):
    A = F.areas()
    return int(np.where(A["area_id"].values == int(area_id))[0][0])


def _history_hourly(table, col, area_id, hours=24):
    df = read_sql(f"SELECT timestamp, {col} AS v FROM {table} WHERE location_id = :a ORDER BY timestamp DESC LIMIT :n",
                  {"a": int(area_id), "n": hours})
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp")


# ----------------------------------------------------------------------------- city overview
def overview() -> dict:
    return F._cached(("overview",), _overview)


def _overview() -> dict:
    A = F.areas()
    lt, la = F.latest_traffic().set_index("area_id"), F.latest_aqi().set_index("area_id")
    tf, aq = F.traffic_forecast(48), F.aqi_forecast(48)
    acc = F.accident_now().set_index("area_id")
    wa, ws = F.water_forecast(7), F.waste_forecast(7)
    el = F.electricity_forecast(48)

    rows = []
    for i, a in A.iterrows():
        aid = int(a["area_id"])
        t_next = tf["values"][i, :6]
        wb, sb = wa["history"].iloc[i, :-1].mean(), ws["history"].iloc[i, :-1].mean()
        w_today, s_today = wa["today"][i], ws["today"][i]
        rows.append({
            "id": aid, "name": a["name"], "lat": a["lat"], "lng": a["lng"], "area_type": a["area_type"],
            "population_k": a["population_k"],
            "traffic": {"value": _f(lt.loc[aid, "traffic_index"]), "level": traffic_level(lt.loc[aid, "traffic_index"]),
                        "speed": _f(lt.loc[aid, "avg_speed"]), "peak_next6": _f(t_next.max()),
                        "peak_next6_level": traffic_level(t_next.max())},
            "aqi": {"value": int(la.loc[aid, "aqi"]), "category": aqi_category(la.loc[aid, "aqi"]),
                    "peak_next24": int(aq["values"][i, :24].max())},
            "water": {"today": _f(w_today, 2), "tomorrow": _f(wa["values"][i, 0], 2), "baseline": _f(wb, 2),
                      "status": status_from_ratio(w_today / wb), "change_pct": pct_change(wa["values"][i, 0], w_today)},
            "waste": {"today": _f(s_today, 2), "tomorrow": _f(ws["values"][i, 0], 2), "baseline": _f(sb, 2),
                      "status": status_from_ratio(s_today / sb, hi=1.10, lo=0.90),
                      "change_pct": pct_change(ws["values"][i, 0], s_today)},
            "accident": {"risk_pct": _f(acc.loc[aid, "risk_pct"]), "level": acc.loc[aid, "level"]},
        })

    t_avg = float(np.mean([r["traffic"]["value"] for r in rows]))
    a_avg = float(np.mean([r["aqi"]["value"] for r in rows]))
    w_tot, w_base = sum(r["water"]["today"] for r in rows), sum(r["water"]["baseline"] for r in rows)
    s_tot, s_base = sum(r["waste"]["today"] for r in rows), sum(r["waste"]["baseline"] for r in rows)
    cur_mw = float(el["history"]["demand_mw"].iloc[-1])
    nxt24 = el["values"][:24]
    pk_i = int(np.argmax(nxt24))
    open_c = Complaint.query.filter(Complaint.status != "Resolved").count()
    high_c = Complaint.query.filter(Complaint.status != "Resolved", Complaint.priority == "HIGH").count()
    return {
        "generated_at": iso(pd.Timestamp.now()), "data_time": iso(F.latest_traffic()["ts"].max()),
        "areas": rows,
        "kpis": {
            "traffic": {"value": _f(t_avg), "level": traffic_level(t_avg),
                        "high_areas": sum(r["traffic"]["level"] in ("HIGH", "VERY HIGH") for r in rows)},
            "aqi": {"value": int(a_avg), "category": aqi_category(a_avg),
                    "worst_area": max(rows, key=lambda r: r["aqi"]["value"])["name"]},
            "water": {"total_ml": _f(w_tot, 1), "status": status_from_ratio(w_tot / w_base), "tomorrow_ml": _f(sum(r["water"]["tomorrow"] for r in rows), 1)},
            "waste": {"total_tons": _f(s_tot, 1), "status": status_from_ratio(s_tot / s_base, 1.10, .9),
                      "tomorrow_tons": _f(sum(r["waste"]["tomorrow"] for r in rows), 1)},
            "electricity": {"now_mw": _f(cur_mw, 0), "peak_mw": _f(nxt24[pk_i], 0), "peak_time": hlabel(el["times"][pk_i])},
            "accident": {"high_risk_areas": sum(r["accident"]["level"] == "HIGH" for r in rows)},
            "complaints": {"open": open_c, "high_priority": high_c},
            "alerts": Alert.query.filter_by(is_active=True).count(),
        },
        "city_traffic_24h": [{"time": iso(t), "label": hlabel(t), "value": _f(tf["values"][:, j].mean())}
                             for j, t in enumerate(tf["times"][:24])],
        "city_aqi_24h": [{"time": iso(t), "label": hlabel(t), "value": int(aq["values"][:, j].mean())}
                         for j, t in enumerate(aq["times"][:24])],
    }


# ----------------------------------------------------------------------------- traffic
def traffic_payload(area_id) -> dict:
    A, i, a = F.areas(), _pos(area_id), _area_row(area_id)
    tf = F.traffic_forecast(48)
    lt = F.latest_traffic().set_index("area_id").loc[int(area_id)]
    hist = _history_hourly("traffic_data", "traffic_index", area_id, 12)
    fc = [{"time": iso(t), "label": hlabel(t), "value": _f(tf["values"][i, j]), "level": traffic_level(tf["values"][i, j])}
          for j, t in enumerate(tf["times"][:12])]
    ranking = []
    for k, r in A.iterrows():
        v = tf["values"][k, :12]
        ranking.append({"area_id": int(r["area_id"]), "name": r["name"], "now": _f(tf["now"][k]), "now_level": traffic_level(tf["now"][k]),
                        "peak": _f(v.max()), "peak_level": traffic_level(v.max()), "peak_time": hlabel(tf["times"][int(v.argmax())])})
    ranking.sort(key=lambda x: -x["peak"])
    return {
        "area": {"id": int(area_id), "name": a["name"], "road_type": a["road_type"]},
        "current": {"value": _f(lt["traffic_index"]), "level": traffic_level(lt["traffic_index"]), "speed": _f(lt["avg_speed"]),
                    "vehicles": int(lt["vehicle_count"]), "weather": lt["weather"], "time": iso(lt["ts"])},
        "history": [{"time": iso(r.timestamp), "label": hlabel(r.timestamp), "value": _f(r.v)} for r in hist.itertuples()],
        "forecast": fc, "ranking": ranking,
        "city_24h": [{"label": hlabel(t), "value": _f(tf["values"][:, j].mean())} for j, t in enumerate(tf["times"][:24])],
        "model": model_summary("traffic"),
    }


# ----------------------------------------------------------------------------- AQI
PERIODS = [("Morning", range(6, 12)), ("Afternoon", range(12, 17)), ("Evening", range(17, 21)), ("Night", [21, 22, 23, 0, 1, 2, 3, 4, 5])]


def aqi_payload(area_id) -> dict:
    A, i, a = F.areas(), _pos(area_id), _area_row(area_id)
    aq = F.aqi_forecast(48)
    la = F.latest_aqi().set_index("area_id").loc[int(area_id)]
    hist = _history_hourly("air_quality", "aqi", area_id, 24)
    times = aq["times"]
    tomorrow = (pd.Timestamp(F.latest_aqi()["ts"].max()).normalize() + pd.Timedelta(days=1)).date()
    periods = []
    for name, hrs in PERIODS:
        vals = [aq["values"][i, j] for j, t in enumerate(times) if t.date() == tomorrow and t.hour in hrs]
        if vals:
            v = float(np.mean(vals))
            periods.append({"name": name, "value": int(v), "category": aqi_category(v)})
    pol = {k: _f(la[k], 2 if k == "co" else 1) for k in ("pm25", "pm10", "no2", "so2", "co", "o3")}
    subs = sub_indices(la["pm25"], la["pm10"], la["no2"], la["so2"], la["co"], la["o3"])
    dominant = max(subs, key=subs.get)
    ranking = [{"area_id": int(r["area_id"]), "name": r["name"], "now": int(aq["now"][k]), "category": aqi_category(aq["now"][k]),
                "peak": int(aq["values"][k, :24].max()), "peak_category": aqi_category(aq["values"][k, :24].max())}
               for k, r in A.iterrows()]
    ranking.sort(key=lambda x: -x["now"])
    return {
        "area": {"id": int(area_id), "name": a["name"]},
        "current": {"aqi": int(la["aqi"]), "category": aqi_category(la["aqi"]), "pollutants": pol, "dominant": dominant,
                    "temperature": _f(la["temperature"]), "humidity": _f(la["humidity"]), "wind": _f(la["wind_speed"]),
                    "time": iso(la["ts"])},
        "history": [{"label": hlabel(r.timestamp), "time": iso(r.timestamp), "value": int(r.v)} for r in hist.itertuples()],
        "forecast": [{"time": iso(t), "label": hlabel(t), "value": int(aq["values"][i, j]), "category": aqi_category(aq["values"][i, j])}
                     for j, t in enumerate(times[:24])],
        "tomorrow": periods, "ranking": ranking,
        "city_avg": int(np.mean(aq["now"])), "city_category": aqi_category(np.mean(aq["now"])),
        "model": model_summary("aqi"),
    }


# ----------------------------------------------------------------------------- accident
def _accident_row_dict(r) -> dict:
    return {k: (float(r[k]) if k not in ("is_night", "has_junction", "hist_accidents") else int(r[k]))
            for k in ("traffic_index", "rain_mm", "visibility_km", "is_night", "hist_accidents", "has_junction", "avg_speed")}


def accident_payload(area_id) -> dict:
    A, i, a = F.areas(), _pos(area_id), _area_row(area_id)
    now = F.accident_now().set_index("area_id")
    fc = F.accident_forecast(12)
    r = now.loc[int(area_id)]
    factors = F.accident_factors(_accident_row_dict(r))
    ranking = []
    for k, ar in A.iterrows():
        rr = now.loc[int(ar["area_id"])]
        ranking.append({"area_id": int(ar["area_id"]), "name": ar["name"], "risk_pct": _f(rr["risk_pct"]), "level": rr["level"],
                        "peak_risk": _f(fc["risk"][k].max()), "peak_time": hlabel(fc["times"][int(fc["risk"][k].argmax())])})
    ranking.sort(key=lambda x: -x["risk_pct"])
    m = active_model("accident")
    import json
    return {
        "area": {"id": int(area_id), "name": a["name"], "junction": bool(a["has_junction"]), "hist": int(a["accident_hist"])},
        "current": {"risk_pct": _f(r["risk_pct"]), "level": r["level"], "factors": factors,
                    "inputs": {"traffic_index": _f(r["traffic_index"]), "rain_mm": _f(r["rain_mm"]),
                               "visibility_km": _f(r["visibility_km"]), "speed": _f(r["avg_speed"]), "is_night": int(r["is_night"])}},
        "forecast": [{"time": iso(t), "label": hlabel(t), "risk_pct": _f(fc["risk"][i, j]), "level": RISK_LEVELS[int(fc["level_idx"][i, j])]}
                     for j, t in enumerate(fc["times"])],
        "ranking": ranking,
        "importance": json.loads(m.feature_importance) if m and m.feature_importance else {},
        "model": model_summary("accident"),
    }


def accident_custom(p: dict) -> dict:
    """What-if simulator: user supplies conditions, model returns the risk."""
    a = _area_row(p["area_id"])
    hour = int(p.get("hour", 18))
    idx = float(p.get("traffic_index", 60))
    row = {"timestamp": pd.Timestamp.now().normalize() + pd.Timedelta(hours=hour), "traffic_index": idx,
           "road_code": int(a["road_code"]), "has_junction": int(a["has_junction"]), "rain_mm": float(p.get("rain_mm", 0)),
           "visibility_km": float(p.get("visibility_km", 10)), "avg_speed": float(F.estimate_speed(idx, int(a["road_code"]))),
           "is_night": int(hour >= 19 or hour < 6), "hist_accidents": int(a["accident_hist"])}
    df = pd.DataFrame([row])
    risk, lvl, proba = F.accident_predict(P.accident_features(df))
    return {"risk_pct": _f(risk[0]), "level": RISK_LEVELS[int(lvl[0])],
            "probabilities": {RISK_LEVELS[k]: _f(proba[0][k] * 100) for k in range(3)},
            "factors": F.accident_factors(row)}


# ----------------------------------------------------------------------------- electricity
def electricity_payload() -> dict:
    el = F.electricity_forecast(48)
    hist = el["history"]
    times, vals = el["times"], el["values"]
    A = F.areas()
    today = pd.Timestamp(hist["timestamp"].iloc[-1]).normalize()
    tomorrow = today + pd.Timedelta(days=1)
    today_vals = list(hist[hist["timestamp"].dt.normalize() == today]["demand_mw"]) + [v for t, v in zip(times, vals) if t.normalize() == today]
    tm = [(t, v) for t, v in zip(times, vals) if t.normalize() == tomorrow]
    pk_t, pk_v = max(tm, key=lambda x: x[1])
    share = (A["population_k"] * (1 + A["commercial_index"])).values
    share = share / share.sum()
    cur = float(hist["demand_mw"].iloc[-1])
    return {
        "current": {"mw": _f(cur, 0), "time": iso(hist["timestamp"].iloc[-1])},
        "today_avg": _f(np.mean(today_vals), 0), "tomorrow_avg": _f(np.mean([v for _, v in tm]), 0),
        "peak": {"mw": _f(pk_v, 0), "time": hlabel(pk_t), "label": "Tomorrow"},
        "change_pct": pct_change(np.mean([v for _, v in tm]), np.mean(today_vals)),
        "history": [{"label": hlabel(r.timestamp), "time": iso(r.timestamp), "value": _f(r.demand_mw, 0)} for r in hist.tail(24).itertuples()],
        "forecast": [{"label": hlabel(t), "time": iso(t), "value": _f(v, 0)} for t, v in zip(times, vals)],
        "areas": sorted([{"area_id": int(r["area_id"]), "name": r["name"], "mw": _f(cur * share[k], 1), "share_pct": _f(share[k] * 100, 1)}
                         for k, r in A.iterrows()], key=lambda x: -x["mw"]),
        "model": model_summary("electricity"),
    }


# ----------------------------------------------------------------------------- water / waste
def water_payload(area_id) -> dict:
    A, i, a = F.areas(), _pos(area_id), _area_row(area_id)
    w = F.water_forecast(7)
    hist = w["history"].iloc[i]
    today = float(w["today"][i])
    tomorrow = float(w["values"][i, 0])
    base = float(hist.iloc[:-1].mean())
    rows = []
    for k, r in A.iterrows():
        b = float(w["history"].iloc[k, :-1].mean())
        rows.append({"area_id": int(r["area_id"]), "name": r["name"], "today": _f(w["today"][k], 2), "tomorrow": _f(w["values"][k, 0], 2),
                     "change_pct": pct_change(w["values"][k, 0], w["today"][k]), "status": status_from_ratio(w["today"][k] / b)})
    rows.sort(key=lambda x: -x["today"])
    return {
        "area": {"id": int(area_id), "name": a["name"], "population_k": float(a["population_k"]), "type": a["area_type"]},
        "today": _f(today, 2), "tomorrow": _f(tomorrow, 2), "change_pct": pct_change(tomorrow, today),
        "status": status_from_ratio(today / base), "baseline": _f(base, 2),
        "history": [{"label": pd.Timestamp(d).strftime("%d %b"), "value": _f(v, 2)} for d, v in hist.items()],
        "forecast": [{"label": pd.Timestamp(d).strftime("%a %d"), "value": _f(w["values"][i, j], 2)} for j, d in enumerate(w["dates"])],
        "areas": rows, "city_total_today": _f(w["today"].sum(), 1), "city_total_tomorrow": _f(w["values"][:, 0].sum(), 1),
        "model": model_summary("water"),
    }


def _waste_shares(area_id):
    df = read_sql("SELECT organic_tons, plastic_tons, paper_tons, other_tons, total_tons FROM waste_data WHERE location_id=:a "
                  "ORDER BY date DESC LIMIT 30", {"a": int(area_id)})
    tot = df["total_tons"].sum()
    return {k: float(df[c].sum() / tot) for k, c in (("Organic", "organic_tons"), ("Plastic", "plastic_tons"),
                                                    ("Paper", "paper_tons"), ("Other", "other_tons"))}


def waste_payload(area_id) -> dict:
    A, i, a = F.areas(), _pos(area_id), _area_row(area_id)
    w = F.waste_forecast(7)
    hist = w["history"].iloc[i]
    today, tomorrow = float(w["today"][i]), float(w["values"][i, 0])
    base = float(hist.iloc[:-1].mean())
    shares = _waste_shares(area_id)
    rows = []
    for k, r in A.iterrows():
        b = float(w["history"].iloc[k, :-1].mean())
        tm = float(w["values"][k, 0])
        st = status_from_ratio(tm / b, 1.10, .9)
        rows.append({"area_id": int(r["area_id"]), "name": r["name"], "today": _f(w["today"][k], 1), "tomorrow": _f(tm, 1),
                     "vs_normal_pct": pct_change(tm, b), "status": st, "trucks": int(math.ceil(tm / 3.0)),
                     "action": "Add evening pickup" if st == "HIGH" else "Regular schedule"})
    rows.sort(key=lambda x: -x["tomorrow"])
    return {
        "area": {"id": int(area_id), "name": a["name"]},
        "today": _f(today, 1), "tomorrow": _f(tomorrow, 1), "change_pct": pct_change(tomorrow, today),
        "status": status_from_ratio(tomorrow / base, 1.10, .9), "baseline": _f(base, 1),
        "breakdown": {k: _f(tomorrow * v, 1) for k, v in shares.items()},
        "history": [{"label": pd.Timestamp(d).strftime("%d %b"), "value": _f(v, 1)} for d, v in hist.items()],
        "forecast": [{"label": pd.Timestamp(d).strftime("%a %d"), "value": _f(w["values"][i, j], 1)} for j, d in enumerate(w["dates"])],
        "areas": rows, "city_total_today": _f(w["today"].sum(), 1), "city_total_tomorrow": _f(w["values"][:, 0].sum(), 1),
        "high_zones": [r for r in rows if r["status"] == "HIGH"][:5] or rows[:3],
        "model": model_summary("waste"),
    }


# ----------------------------------------------------------------------------- one-area snapshot (map popup / citizen home)
def area_detail(area_id) -> dict:
    ov = overview()
    row = next(r for r in ov["areas"] if r["id"] == int(area_id))
    acc = F.accident_now().set_index("area_id").loc[int(area_id)]
    factors = F.accident_factors(_accident_row_dict(acc))
    tf = F.traffic_forecast(48)
    i = _pos(area_id)
    alerts = [al.to_dict() for al in Alert.query.filter(Alert.is_active.is_(True)).filter(
        (Alert.location_id == int(area_id)) | (Alert.location_id.is_(None))).order_by(Alert.created_at.desc()).limit(6)]
    return {**row, "accident": {**row["accident"], "factors": factors},
            "traffic_forecast": [{"label": hlabel(t), "value": _f(tf["values"][i, j]), "level": traffic_level(tf["values"][i, j])}
                                 for j, t in enumerate(tf["times"][:8])],
            "alerts": alerts}
