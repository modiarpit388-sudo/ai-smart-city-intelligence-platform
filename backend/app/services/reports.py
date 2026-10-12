"""Analytics & report builder (daily / weekly / monthly / yearly) with CSV export."""
import csv
import io

import numpy as np
import pandas as pd

from ..extensions import db
from ..models import Complaint, MLModel
from ..services.ingest import locations_df, read_sql

WINDOW_DAYS = {"daily": 14, "weekly": 84, "monthly": 185, "yearly": 3650}
KINDS = {
    "traffic": "Traffic Report", "aqi": "Air Quality Report", "accident": "Accident Risk Report",
    "electricity": "Electricity Report", "water": "Water Report", "waste": "Waste Report",
    "complaints": "Complaint Report", "models": "ML Prediction Accuracy Report",
}


def _bucket(ts: pd.Series, period: str) -> pd.Series:
    ts = pd.to_datetime(ts)
    if period == "daily":
        return ts.dt.strftime("%Y-%m-%d")
    if period == "weekly":
        return (ts - pd.to_timedelta(ts.dt.dayofweek, unit="D")).dt.strftime("%Y-%m-%d")
    if period == "monthly":
        return ts.dt.strftime("%Y-%m")
    return ts.dt.strftime("%Y")


def _load(table, cols, tcol, period, area_id=None, has_area=True):
    mx = read_sql(f"SELECT MAX({tcol}) AS m FROM {table}")["m"].iloc[0]
    cut = (pd.Timestamp(mx) - pd.Timedelta(days=WINDOW_DAYS[period])).strftime("%Y-%m-%d")
    sql = f"SELECT {tcol} AS t, {'location_id AS area_id, ' if has_area else ''}{cols} FROM {table} WHERE {tcol} > :cut"
    params = {"cut": cut}
    if area_id and has_area:
        sql += " AND location_id = :a"
        params["a"] = int(area_id)
    df = read_sql(sql, params)
    df["bucket"] = _bucket(df["t"], period)
    if has_area:
        names = locations_df().set_index("id")["name"]
        df["area"] = df["area_id"].map(names)
    return df


def _cols(*pairs):
    return [{"key": k, "label": l} for k, l in pairs]


def _clean(df):
    return df.replace({np.nan: None}).to_dict("records")


def build_report(kind: str, period: str = "daily", area_id=None) -> dict:
    period = period if period in WINDOW_DAYS else "daily"
    out = {"kind": kind, "title": KINDS.get(kind, kind), "period": period}

    if kind == "traffic":
        d = _load("traffic_data", "traffic_index, avg_speed", "timestamp", period, area_id)
        d["high"] = (d["traffic_index"] >= 60).astype(int)
        g = d.groupby("bucket").agg(avg_index=("traffic_index", "mean"), peak_index=("traffic_index", "max"),
                                    avg_speed=("avg_speed", "mean"), high_pct=("high", "mean")).reset_index()
        g["high_pct"] *= 100
        a = d.groupby("area").agg(avg_index=("traffic_index", "mean"), peak_index=("traffic_index", "max"), high_pct=("high", "mean")).reset_index()
        a["high_pct"] *= 100
        out.update(columns=_cols(("bucket", "Period"), ("avg_index", "Avg congestion"), ("peak_index", "Peak"), ("avg_speed", "Avg speed km/h"), ("high_pct", "% hours HIGH")),
                   area_columns=_cols(("area", "Area"), ("avg_index", "Avg congestion"), ("peak_index", "Peak"), ("high_pct", "% hours HIGH")),
                   chart=["avg_index", "peak_index"])
    elif kind == "aqi":
        d = _load("air_quality", "aqi, pm25, category", "timestamp", period, area_id)
        g = d.groupby("bucket").agg(avg_aqi=("aqi", "mean"), max_aqi=("aqi", "max"), avg_pm25=("pm25", "mean")).reset_index()
        a = d.groupby("area").agg(avg_aqi=("aqi", "mean"), max_aqi=("aqi", "max"), avg_pm25=("pm25", "mean"),
                                  dominant=("category", lambda s: s.mode().iloc[0])).reset_index()
        out.update(columns=_cols(("bucket", "Period"), ("avg_aqi", "Avg AQI"), ("max_aqi", "Max AQI"), ("avg_pm25", "Avg PM2.5")),
                   area_columns=_cols(("area", "Area"), ("avg_aqi", "Avg AQI"), ("max_aqi", "Max AQI"), ("avg_pm25", "Avg PM2.5"), ("dominant", "Typical category")),
                   chart=["avg_aqi", "max_aqi"])
    elif kind == "accident":
        d = _load("accident_data", "risk_score, risk_level, accident_count", "timestamp", period, area_id)
        d["high"] = (d["risk_level"] == "HIGH").astype(int)
        g = d.groupby("bucket").agg(avg_risk=("risk_score", "mean"), high_hours=("high", "sum"), accidents=("accident_count", "sum")).reset_index()
        g["avg_risk"] *= 100
        a = d.groupby("area").agg(avg_risk=("risk_score", "mean"), high_hours=("high", "sum"), accidents=("accident_count", "sum")).reset_index()
        a["avg_risk"] *= 100
        out.update(columns=_cols(("bucket", "Period"), ("avg_risk", "Avg risk %"), ("high_hours", "HIGH-risk hours"), ("accidents", "Recorded accidents")),
                   area_columns=_cols(("area", "Area"), ("avg_risk", "Avg risk %"), ("high_hours", "HIGH-risk hours"), ("accidents", "Recorded accidents")),
                   chart=["avg_risk"])
    elif kind == "electricity":
        d = _load("electricity_data", "demand_mw", "timestamp", period, has_area=False)
        g = d.groupby("bucket").agg(avg_mw=("demand_mw", "mean"), peak_mw=("demand_mw", "max"), min_mw=("demand_mw", "min")).reset_index()
        a = pd.DataFrame(columns=["area"])
        out.update(columns=_cols(("bucket", "Period"), ("avg_mw", "Avg MW"), ("peak_mw", "Peak MW"), ("min_mw", "Min MW")), area_columns=[], chart=["avg_mw", "peak_mw"])
    elif kind == "water":
        d = _load("water_consumption", "consumption_ml", "date", period, area_id)
        g = d.groupby("bucket").agg(total_ml=("consumption_ml", "sum"), avg_area_ml=("consumption_ml", "mean")).reset_index()
        a = d.groupby("area").agg(total_ml=("consumption_ml", "sum"), avg_daily_ml=("consumption_ml", "mean")).reset_index()
        out.update(columns=_cols(("bucket", "Period"), ("total_ml", "Total (ML)"), ("avg_area_ml", "Avg per area/day (ML)")),
                   area_columns=_cols(("area", "Area"), ("total_ml", "Total (ML)"), ("avg_daily_ml", "Avg daily (ML)")), chart=["total_ml"])
    elif kind == "waste":
        d = _load("waste_data", "total_tons, collected_tons, organic_tons, plastic_tons, paper_tons, other_tons", "date", period, area_id)
        g = d.groupby("bucket").agg(generated=("total_tons", "sum"), collected=("collected_tons", "sum"), organic=("organic_tons", "sum"),
                                    plastic=("plastic_tons", "sum"), paper=("paper_tons", "sum"), other=("other_tons", "sum")).reset_index()
        g["efficiency"] = g["collected"] / g["generated"] * 100
        a = d.groupby("area").agg(generated=("total_tons", "sum"), collected=("collected_tons", "sum")).reset_index()
        a["efficiency"] = a["collected"] / a["generated"] * 100
        out.update(columns=_cols(("bucket", "Period"), ("generated", "Generated (t)"), ("collected", "Collected (t)"), ("efficiency", "Collection %"),
                                 ("organic", "Organic"), ("plastic", "Plastic"), ("paper", "Paper"), ("other", "Other")),
                   area_columns=_cols(("area", "Area"), ("generated", "Generated (t)"), ("collected", "Collected (t)"), ("efficiency", "Collection %")),
                   chart=["generated", "collected"])
    elif kind == "complaints":
        rows = Complaint.query.all()
        df = pd.DataFrame([{"t": c.created_at, "status": c.status, "category": c.category.name if c.category else "-",
                            "department": c.department.name if c.department else "-", "priority": c.priority,
                            "hours": ((c.resolved_at - c.created_at).total_seconds() / 3600) if c.resolved_at else None} for c in rows])
        if df.empty:
            df = pd.DataFrame(columns=["t", "status", "category", "department", "priority", "hours"])
            df["t"] = pd.to_datetime(df["t"])
        df["bucket"] = _bucket(df["t"], period)
        df["resolved"] = (df["status"] == "Resolved").astype(int)
        df["pending"] = 1 - df["resolved"]
        df["high"] = (df["priority"] == "HIGH").astype(int)
        g = df.groupby("bucket").agg(total=("t", "count"), resolved=("resolved", "sum"), pending=("pending", "sum"), high=("high", "sum")).reset_index()
        a = df.groupby("category").agg(total=("t", "count"), resolved=("resolved", "sum"), pending=("pending", "sum"),
                                       avg_hours=("hours", "mean"), department=("department", "first")).reset_index()
        out.update(columns=_cols(("bucket", "Period"), ("total", "Total"), ("resolved", "Resolved"), ("pending", "Pending"), ("high", "High priority")),
                   area_columns=_cols(("category", "Category"), ("department", "Department"), ("total", "Total"), ("resolved", "Resolved"), ("pending", "Pending"), ("avg_hours", "Avg resolution (h)")),
                   chart=["total", "resolved"], by_label="By category")
    elif kind == "models":
        rows = []
        for m in MLModel.query.filter_by(is_active=True).order_by(MLModel.module).all():
            met = {x.name: x.value for x in m.metrics}
            rows.append({"module": m.module, "algorithm": m.algorithm, "trained": m.trained_at.strftime("%Y-%m-%d %H:%M"), "version": m.version,
                         "train_rows": m.train_rows, **{k: round(v, 4) for k, v in met.items()}})
        out.update(columns=_cols(("module", "Module"), ("algorithm", "Algorithm"), ("version", "Version"), ("train_rows", "Train rows"), ("RMSE", "RMSE"), ("MAE", "MAE"), ("R2", "R²"),
                                 ("Accuracy", "Accuracy"), ("Precision", "Precision"), ("Recall", "Recall"), ("F1", "F1")),
                   area_columns=[], chart=[], rows=rows, by_area=[])
        return out
    else:
        raise KeyError(kind)

    g = g.sort_values("bucket")
    for c in g.columns:
        if g[c].dtype.kind == "f":
            g[c] = g[c].round(2)
    for c in a.columns:
        if a[c].dtype.kind == "f":
            a[c] = a[c].round(2)
    out["rows"] = _clean(g)
    out["by_area"] = _clean(a) if len(a) else []
    return out


def to_csv(rep: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = rep["columns"]
    w.writerow([c["label"] for c in cols])
    for r in rep["rows"]:
        w.writerow([r.get(c["key"]) for c in cols])
    if rep.get("by_area"):
        w.writerow([])
        acols = rep["area_columns"]
        w.writerow([c["label"] for c in acols])
        for r in rep["by_area"]:
            w.writerow([r.get(c["key"]) for c in acols])
    return buf.getvalue()
