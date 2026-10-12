"""
Data ingestion: keeps the monitoring tables current.

* First start  -> generates HOURLY_HISTORY_DAYS of hourly data and DAILY_HISTORY_DAYS of daily data.
* Every later call -> "catches up" from the last stored reading to the current hour/day.

In production this module is where real IoT sensors / open-data APIs would be plugged in.
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import current_app
from sqlalchemy import func, text

from ..extensions import db
from ..models import (AccidentData, AirQuality, ElectricityData, Location, TrafficData,
                      WasteData, WaterConsumption)
from ..simulation.generators import (enrich_areas, gen_electricity, gen_hourly, gen_waste,
                                     gen_water)

TABLES = {
    "traffic_data": TrafficData, "accident_data": AccidentData, "air_quality": AirQuality,
    "electricity_data": ElectricityData, "water_consumption": WaterConsumption, "waste_data": WasteData,
}


def locations_df() -> pd.DataFrame:
    rows = Location.query.order_by(Location.id).all()
    df = pd.DataFrame([{c.name: getattr(r, c.name) for c in Location.__table__.columns} for r in rows])
    return enrich_areas(df)


def insert_df(model, df: pd.DataFrame, chunk: int = 4000):
    if df is None or df.empty:
        return 0
    records = df.to_dict("records")
    for i in range(0, len(records), chunk):
        db.session.execute(model.__table__.insert(), records[i:i + chunk])
    db.session.commit()
    return len(records)


def _now_hour() -> datetime:
    return datetime.now().replace(minute=0, second=0, microsecond=0)


def _last(col):
    return db.session.query(func.max(col)).scalar()


def ensure_data_current(verbose: bool = False) -> dict:
    """Insert every missing hour/day up to 'now'. Returns rows added per table."""
    cfg = current_app.config
    areas = locations_df()
    now_h = _now_hour()
    today = pd.Timestamp(now_h).normalize()
    added = {}

    # ---- hourly per-area tables (traffic + air + accident share one generator)
    last_ts = _last(TrafficData.timestamp)
    start = now_h - timedelta(days=cfg["HOURLY_HISTORY_DAYS"]) if last_ts is None else last_ts + timedelta(hours=1)
    if start <= now_h:
        times = pd.date_range(start - timedelta(hours=1), now_h, freq="h")
        seed = int(start.timestamp()) % 100000
        tr, aq, ac = gen_hourly(times, areas, seed=seed)
        added["traffic_data"] = insert_df(TrafficData, tr)
        added["air_quality"] = insert_df(AirQuality, aq)
        added["accident_data"] = insert_df(AccidentData, ac)

    # ---- electricity (city-level hourly)
    last_e = _last(ElectricityData.timestamp)
    start_e = now_h - timedelta(days=cfg["ELECTRICITY_HISTORY_DAYS"]) if last_e is None else last_e + timedelta(hours=1)
    if start_e <= now_h:
        times = pd.date_range(start_e, now_h, freq="h")
        added["electricity_data"] = insert_df(ElectricityData, gen_electricity(times, seed=int(start_e.timestamp()) % 100000))

    # ---- water + waste (area-level daily)
    last_w = _last(WaterConsumption.date)
    d0 = (today - pd.Timedelta(days=cfg["DAILY_HISTORY_DAYS"] - 1)) if last_w is None else pd.Timestamp(last_w) + pd.Timedelta(days=1)
    if d0 <= today:
        days = pd.date_range(d0, today, freq="D")
        added["water_consumption"] = insert_df(WaterConsumption, gen_water(days, areas, seed=int(d0.timestamp()) % 100000))
    last_ws = _last(WasteData.date)
    d1 = (today - pd.Timedelta(days=cfg["DAILY_HISTORY_DAYS"] - 1)) if last_ws is None else pd.Timestamp(last_ws) + pd.Timedelta(days=1)
    if d1 <= today:
        days = pd.date_range(d1, today, freq="D")
        added["waste_data"] = insert_df(WasteData, gen_waste(days, areas, seed=int(d1.timestamp()) % 100000 + 7))

    if any(added.values()):
        from ..ml.forecast import clear_cache
        clear_cache()
    if verbose:
        print("   ingested:", {k: v for k, v in added.items() if v})
    return added


def dataset_summary() -> list:
    out = []
    for name, model in TABLES.items():
        n = db.session.query(func.count()).select_from(model).scalar()
        ts_col = getattr(model, "timestamp", None) or getattr(model, "date")
        out.append({
            "table": name, "rows": n,
            "first": (_last_min := db.session.query(func.min(ts_col)).scalar()) and str(_last_min),
            "last": (lm := db.session.query(func.max(ts_col)).scalar()) and str(lm),
            "columns": [c.name for c in model.__table__.columns if c.name != "id"],
        })
    return out


def read_sql(sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql(text(sql), db.engine, params=params or {})
