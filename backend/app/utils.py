"""Shared helpers: level classification, CPCB AQI computation, time features."""
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ traffic
TRAFFIC_LEVELS = ["LOW", "MEDIUM", "HIGH", "VERY HIGH"]


def traffic_level(v) -> str:
    v = float(v)
    if v < 35:
        return "LOW"
    if v < 60:
        return "MEDIUM"
    if v < 80:
        return "HIGH"
    return "VERY HIGH"


# ------------------------------------------------------------------ AQI (Indian CPCB scale)
_BP = {
    "pm25": ([0, 30, 60, 90, 120, 250, 380], [0, 50, 100, 200, 300, 400, 500]),
    "pm10": ([0, 50, 100, 250, 350, 430, 600], [0, 50, 100, 200, 300, 400, 500]),
    "no2": ([0, 40, 80, 180, 280, 400, 600], [0, 50, 100, 200, 300, 400, 500]),
    "so2": ([0, 40, 80, 380, 800, 1600, 2400], [0, 50, 100, 200, 300, 400, 500]),
    "co": ([0, 1, 2, 10, 17, 34, 50], [0, 50, 100, 200, 300, 400, 500]),
    "o3": ([0, 50, 100, 168, 208, 748, 1000], [0, 50, 100, 200, 300, 400, 500]),
}
AQI_BINS = [50, 100, 200, 300, 400]
AQI_LABELS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def aqi_from_pollutants(pm25, pm10, no2, so2, co, o3):
    """Overall AQI = max of the pollutant sub-indices (CPCB method)."""
    subs = [np.interp(np.asarray(v, dtype=float), *_BP[k]) for k, v in
            (("pm25", pm25), ("pm10", pm10), ("no2", no2), ("so2", so2), ("co", co), ("o3", o3))]
    return np.round(np.max(subs, axis=0), 0)


def sub_indices(pm25, pm10, no2, so2, co, o3) -> dict:
    return {k: float(np.interp(float(v), *_BP[k])) for k, v in
            (("pm25", pm25), ("pm10", pm10), ("no2", no2), ("so2", so2), ("co", co), ("o3", o3))}


def aqi_category(v) -> str:
    return AQI_LABELS[int(np.searchsorted(AQI_BINS, float(v), side="left"))]


# ------------------------------------------------------------------ accident risk
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
RISK_WEIGHTS = np.array([0.15, 0.55, 0.95])  # expected risk % per class (for the risk gauge)


def risk_label_from_score(score):
    s = np.asarray(score, dtype=float)
    return np.where(s < 0.32, "LOW", np.where(s < 0.52, "MEDIUM", "HIGH"))


# ------------------------------------------------------------------ generic
def hour_features(ts) -> pd.DataFrame:
    t = pd.DatetimeIndex(ts)
    return pd.DataFrame({
        "hour_sin": np.sin(2 * np.pi * t.hour / 24), "hour_cos": np.cos(2 * np.pi * t.hour / 24),
        "dow": t.dayofweek, "is_weekend": (t.dayofweek >= 5).astype(int), "month": t.month,
    }, index=range(len(t)))


def pct_change(new, old):
    return 0.0 if not old else round((new - old) / old * 100.0, 1)


def iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")
