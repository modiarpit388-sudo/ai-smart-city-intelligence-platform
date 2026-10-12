"""
Deterministic synthetic weather + holiday calendar for Bengaluru.

The weather is a pure function of the timestamp (pseudo-random values are derived from a
hash of the date), so the *same* function produces both historical observations and
"forecast" weather for future hours. This lets the ML services use weather forecasts
exactly like a real system would use a meteorological API.
"""
import numpy as np
import pandas as pd

MONTH_MEAN_TEMP = np.array([22.5, 24.5, 27.0, 29.0, 28.0, 25.0, 24.0, 24.0, 24.5, 24.5, 23.0, 22.0])
RAIN_PROB = np.array([.03, .03, .05, .20, .35, .55, .60, .60, .70, .60, .30, .08])

# Approximate (month, day) calendar – enough to give the models a holiday signal.
HOLIDAYS = {(1, 1), (1, 14), (1, 26), (3, 30), (5, 1), (8, 15), (9, 7), (10, 2), (10, 20), (11, 1), (11, 8), (12, 25)}
FESTIVAL_DAYS = {(1, 14), (3, 30), (8, 27), (9, 7), (9, 8), (10, 2), (10, 3), (10, 20), (11, 8), (11, 9), (12, 25)}


def _flags(idx, table):
    idx = pd.DatetimeIndex(idx)
    return np.array([(m, d) in table for m, d in zip(idx.month, idx.day)], dtype=int)


def is_holiday(idx):
    return _flags(idx, HOLIDAYS)


def is_festival(idx):
    return _flags(idx, FESTIVAL_DAYS)


def _hash(x, salt):
    v = np.sin((np.asarray(x, dtype=float) + salt) * 12.9898) * 43758.5453
    return v - np.floor(v)


def weather_frame(times) -> pd.DataFrame:
    t = pd.DatetimeIndex(times)
    hour = t.hour.values + t.minute.values / 60.0
    month = t.month.values - 1
    day_key = (t.year.values * 400 + t.dayofyear.values).astype(float)
    hr_key = day_key * 24 + t.hour.values

    rain_day = _hash(day_key, 1) < RAIN_PROB[month]
    start = 13 + 6 * _hash(day_key, 2)
    dur = 1.5 + 4 * _hash(day_key, 3)
    intensity = 2 + 14 * _hash(day_key, 4)
    centre = start + dur / 2
    shape = np.exp(-(((hour - centre) / (dur / 2 + 0.6)) ** 2))
    rain = np.where(rain_day, intensity * shape * (0.6 + 0.8 * _hash(hr_key, 5)), 0.0)
    rain = np.where(rain < 0.3, 0.0, rain)

    temp = (MONTH_MEAN_TEMP[month] + 5.0 * np.sin(2 * np.pi * (hour - 9) / 24)
            + (_hash(day_key, 6) - 0.5) * 3.0 - np.minimum(0.45 * rain, 4.0))
    humidity = np.clip(76 - 2.4 * (temp - 24) + np.where(rain > 0, 14, 0) + (_hash(hr_key, 7) - 0.5) * 8, 28, 98)
    wind = np.clip(6 + 8 * _hash(day_key, 8) + 3 * np.sin(2 * np.pi * (hour - 14) / 24) + (_hash(hr_key, 9) - 0.5) * 3, 2, 30)
    vis = 10 - 0.55 * np.minimum(rain, 12)
    fog = ((month == 11) | (month == 0)) & (hour < 8)
    vis = vis - np.where(fog, 4.5 * _hash(day_key, 10), 0)
    vis = np.clip(vis, 0.8, 10.0)
    cloudy = _hash(day_key, 11) < 0.4
    label = np.where(rain > 5, "Heavy Rain", np.where(rain > 0.3, "Rain", np.where(cloudy, "Cloudy", "Clear")))

    return pd.DataFrame({
        "temperature": np.round(temp, 1), "humidity": np.round(humidity, 1),
        "wind_speed": np.round(wind, 1), "rain_mm": np.round(rain, 2),
        "visibility_km": np.round(vis, 1), "weather": label,
    }, index=t)


def daily_weather(dates) -> pd.DataFrame:
    """Daily aggregates (temp_max, rain_mm) for a sequence of dates."""
    d = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize()
    if len(d) == 0:
        return pd.DataFrame(columns=["temp_max", "rain_mm"])
    hours = pd.date_range(d.min(), d.max() + pd.Timedelta(hours=23), freq="h")
    w = weather_frame(hours)
    g = w.groupby(w.index.normalize()).agg(temp_max=("temperature", "max"), rain_mm=("rain_mm", "sum"))
    return g.reindex(d)
