"""
Feature engineering + training pipelines for the six numeric modules.

The `*_features()` functions are used BOTH at training time (whole history at once) and at
prediction time (one future step at a time) so that there is never a train/serve mismatch.
"""
import numpy as np
import pandas as pd

from ..services.ingest import locations_df, read_sql
from ..simulation.weather import is_festival, is_holiday
from ..utils import RISK_LEVELS
from .registry import latest_test_mask, train_classification, train_regression

TEST_DAYS = 14


def _area_static() -> pd.DataFrame:
    a = locations_df().rename(columns={"id": "area_id"})
    return a


def _sincos(ts):
    t = pd.DatetimeIndex(ts)
    return np.sin(2 * np.pi * t.hour / 24), np.cos(2 * np.pi * t.hour / 24)


# ================================================================== TRAFFIC
TRAFFIC_FEATURES = ["area_id", "traffic_base", "road_code", "has_junction", "commercial_index", "hour_sin",
                    "hour_cos", "dow", "is_weekend", "is_holiday", "rain_mm", "temperature", "prev_index"]


def traffic_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.DatetimeIndex(df["timestamp"])
    hs, hc = _sincos(ts)
    return pd.DataFrame({
        "area_id": df["area_id"].values, "traffic_base": df["traffic_base"].values,
        "road_code": df["road_code"].values, "has_junction": df["has_junction"].values,
        "commercial_index": df["commercial_index"].values, "hour_sin": hs, "hour_cos": hc,
        "dow": ts.dayofweek.values, "is_weekend": (ts.dayofweek.values >= 5).astype(int),
        "is_holiday": is_holiday(ts), "rain_mm": df["rain_mm"].values,
        "temperature": df["temperature"].values, "prev_index": df["prev_index"].values,
    })[TRAFFIC_FEATURES]


def train_traffic(log=print):
    df = read_sql("SELECT timestamp, location_id AS area_id, traffic_index, prev_traffic_index AS prev_index, "
                  "rain_mm, temperature FROM traffic_data")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.merge(_area_static(), on="area_id").sort_values("timestamp").reset_index(drop=True)
    X, y = traffic_features(df), df["traffic_index"]
    return train_regression("traffic", X, y, latest_test_mask(df["timestamp"], TEST_DAYS), log=log)


# ================================================================== AIR QUALITY
AQI_FEATURES = ["area_id", "pollution_base", "industrial_index", "hour_sin", "hour_cos", "dow", "is_weekend",
                "temperature", "humidity", "wind_speed", "rain_mm", "traffic_index", "aqi_prev"]


def aqi_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.DatetimeIndex(df["timestamp"])
    hs, hc = _sincos(ts)
    out = pd.DataFrame({
        "area_id": df["area_id"].values, "pollution_base": df["pollution_base"].values,
        "industrial_index": df["industrial_index"].values, "hour_sin": hs, "hour_cos": hc,
        "dow": ts.dayofweek.values, "is_weekend": (ts.dayofweek.values >= 5).astype(int),
        "temperature": df["temperature"].values, "humidity": df["humidity"].values,
        "wind_speed": df["wind_speed"].values, "rain_mm": df["rain_mm"].values,
        "traffic_index": df["traffic_index"].values, "aqi_prev": df["aqi_prev"].values,
    })
    return out[AQI_FEATURES]


def train_aqi(log=print):
    df = read_sql("SELECT timestamp, location_id AS area_id, aqi, temperature, humidity, wind_speed, rain_mm, "
                  "traffic_index FROM air_quality")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.merge(_area_static(), on="area_id").sort_values(["area_id", "timestamp"]).reset_index(drop=True)
    df["aqi_prev"] = df.groupby("area_id")["aqi"].shift(1)
    df = df.dropna(subset=["aqi_prev"]).reset_index(drop=True)
    X, y = aqi_features(df), df["aqi"]
    return train_regression("aqi", X, y, latest_test_mask(df["timestamp"], TEST_DAYS), log=log)


# ================================================================== ELECTRICITY
ELEC_FEATURES = ["hour_sin", "hour_cos", "dow", "is_weekend", "month", "is_holiday", "temperature", "humidity",
                 "lag1", "lag24"]


def elec_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.DatetimeIndex(df["timestamp"])
    hs, hc = _sincos(ts)
    return pd.DataFrame({
        "hour_sin": hs, "hour_cos": hc, "dow": ts.dayofweek.values,
        "is_weekend": (ts.dayofweek.values >= 5).astype(int), "month": ts.month.values,
        "is_holiday": is_holiday(ts), "temperature": df["temperature"].values,
        "humidity": df["humidity"].values, "lag1": df["lag1"].values, "lag24": df["lag24"].values,
    })[ELEC_FEATURES]


def train_electricity(log=print):
    df = read_sql("SELECT timestamp, demand_mw, temperature, humidity FROM electricity_data ORDER BY timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["lag1"], df["lag24"] = df["demand_mw"].shift(1), df["demand_mw"].shift(24)
    df = df.dropna().reset_index(drop=True)
    X, y = elec_features(df), df["demand_mw"]
    return train_regression("electricity", X, y, latest_test_mask(df["timestamp"], TEST_DAYS), log=log)


# ================================================================== WATER
WATER_FEATURES = ["population_k", "type_code", "month", "dow", "is_weekend", "is_holiday", "temp_max", "rain_mm",
                  "prev_day", "prev_week"]


def water_features(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.DatetimeIndex(df["date"])
    return pd.DataFrame({
        "population_k": df["population_k"].values, "type_code": df["type_code"].values,
        "month": d.month.values, "dow": d.dayofweek.values, "is_weekend": (d.dayofweek.values >= 5).astype(int),
        "is_holiday": is_holiday(d), "temp_max": df["temp_max"].values, "rain_mm": df["rain_mm"].values,
        "prev_day": df["prev_day"].values, "prev_week": df["prev_week"].values,
    })[WATER_FEATURES]


def train_water(log=print):
    df = read_sql("SELECT date, location_id AS area_id, consumption_ml, temp_max, rainfall_mm AS rain_mm FROM water_consumption")
    df["date"] = pd.to_datetime(df["date"])
    df = df.merge(_area_static(), on="area_id").sort_values(["area_id", "date"]).reset_index(drop=True)
    g = df.groupby("area_id")["consumption_ml"]
    df["prev_day"], df["prev_week"] = g.shift(1), g.shift(7)
    df = df.dropna(subset=["prev_day", "prev_week"]).reset_index(drop=True)
    X, y = water_features(df), df["consumption_ml"]
    return train_regression("water", X, y, latest_test_mask(df["date"], 21), log=log)


# ================================================================== WASTE
WASTE_FEATURES = ["population_k", "commercial_index", "dow", "is_weekend", "is_holiday", "is_festival", "temp_max",
                  "rain_mm", "month", "prev_day", "prev_week"]


def waste_features(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.DatetimeIndex(df["date"])
    return pd.DataFrame({
        "population_k": df["population_k"].values, "commercial_index": df["commercial_index"].values,
        "dow": d.dayofweek.values, "is_weekend": (d.dayofweek.values >= 5).astype(int),
        "is_holiday": is_holiday(d), "is_festival": is_festival(d), "temp_max": df["temp_max"].values,
        "rain_mm": df["rain_mm"].values, "month": d.month.values,
        "prev_day": df["prev_day"].values, "prev_week": df["prev_week"].values,
    })[WASTE_FEATURES]


def train_waste(log=print):
    df = read_sql("SELECT date, location_id AS area_id, total_tons, temp_max, rainfall_mm AS rain_mm FROM waste_data")
    df["date"] = pd.to_datetime(df["date"])
    df = df.merge(_area_static(), on="area_id").sort_values(["area_id", "date"]).reset_index(drop=True)
    g = df.groupby("area_id")["total_tons"]
    df["prev_day"], df["prev_week"] = g.shift(1), g.shift(7)
    df = df.dropna(subset=["prev_day", "prev_week"]).reset_index(drop=True)
    X, y = waste_features(df), df["total_tons"]
    return train_regression("waste", X, y, latest_test_mask(df["date"], 21), log=log)


# ================================================================== ACCIDENT RISK (classification)
ACC_FEATURES = ["traffic_index", "road_code", "has_junction", "rain_mm", "visibility_km", "avg_speed", "is_night",
                "hour_sin", "hour_cos", "is_weekend", "hist_accidents"]


def accident_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.DatetimeIndex(df["timestamp"])
    hs, hc = _sincos(ts)
    return pd.DataFrame({
        "traffic_index": df["traffic_index"].values, "road_code": df["road_code"].values,
        "has_junction": df["has_junction"].values, "rain_mm": df["rain_mm"].values,
        "visibility_km": df["visibility_km"].values, "avg_speed": df["avg_speed"].values,
        "is_night": df["is_night"].values, "hour_sin": hs, "hour_cos": hc,
        "is_weekend": (ts.dayofweek.values >= 5).astype(int), "hist_accidents": df["hist_accidents"].values,
    })[ACC_FEATURES]


def train_accident(log=print):
    df = read_sql("SELECT timestamp, traffic_index, road_code, has_junction, rain_mm, visibility_km, avg_speed, "
                  "is_night, hist_accidents, risk_level FROM accident_data")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    mask = latest_test_mask(df["timestamp"], TEST_DAYS)
    rng = np.random.RandomState(1)
    tr = np.where(~mask)[0]
    te = np.where(mask)[0]
    tr = rng.choice(tr, min(len(tr), 30000), replace=False)
    te = rng.choice(te, min(len(te), 8000), replace=False)
    sub = df.iloc[np.concatenate([tr, te])].reset_index(drop=True)
    sub_mask = np.array([False] * len(tr) + [True] * len(te))
    X = accident_features(sub)
    return train_classification("accident", X, sub["risk_level"].values, sub_mask, RISK_LEVELS, log=log)
