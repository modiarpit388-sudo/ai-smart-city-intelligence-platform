"""
Synthetic-but-realistic data generators.

Real city sensors / open-data feeds can replace these generators without touching the rest
of the platform: the ML layer only ever reads the database tables.

Relationships that make the data learnable (and the project explainable in a viva):
  * traffic   = area base * rush-hour profile * weather boost + AR(1) noise
  * AQI       = CPCB sub-index formula on pollutants that depend on traffic, wind, rain, hour
  * accident  = weighted risk score of traffic, rain, visibility, night, junction, history
  * electricity = daily double-peak profile * temperature (AC load) * weekday factor
  * water     = population * per-capita * temperature/weekend/rain factors
  * waste     = population * commercial activity * weekend/festival factors
"""
import numpy as np
import pandas as pd
from scipy.signal import lfilter

from ..utils import aqi_category, aqi_from_pollutants, risk_label_from_score, traffic_level
from .areas import AREA_TYPE_CODE, ROAD_CODE
from .weather import daily_weather, is_festival, is_holiday, weather_frame


def enrich_areas(df: pd.DataFrame) -> pd.DataFrame:
    """Add numeric code columns used as model features."""
    out = df.copy()
    out["road_code"] = out["road_type"].map(ROAD_CODE).astype(int)
    out["type_code"] = out["area_type"].map(AREA_TYPE_CODE).astype(int)
    out["has_junction"] = out["has_junction"].astype(int)
    return out


def _ar(rng, shape, sigma, phi):
    return lfilter([1.0], [1.0, -phi], rng.normal(0, sigma, shape), axis=1)


def _traffic_profile(hour, off):
    h = hour.astype(float)
    weekday = 0.14 + 0.72 * np.exp(-((h - 9.0) / 1.9) ** 2) + 0.80 * np.exp(-((h - 18.4) / 2.1) ** 2) \
        + 0.42 * np.exp(-((h - 13.0) / 3.2) ** 2)
    weekend = 0.12 + 0.35 * np.exp(-((h - 11.5) / 2.6) ** 2) + 0.60 * np.exp(-((h - 19.0) / 2.6) ** 2)
    return np.clip(np.where(off, weekend, weekday), 0.05, 1.05)


def _long(times, area_ids, **cols) -> pd.DataFrame:
    """Flatten (A, T) matrices into a long DataFrame ordered area-major."""
    A, T = len(area_ids), len(times)
    data = {"timestamp": pd.DatetimeIndex(np.tile(times.values, A)), "location_id": np.repeat(area_ids, T)}
    for k, v in cols.items():
        data[k] = np.asarray(v).reshape(-1) if np.ndim(v) == 2 else np.tile(v, A)
    return pd.DataFrame(data)


# ------------------------------------------------------------------------------- hourly
def gen_hourly(times, areas: pd.DataFrame, seed: int = 0):
    """
    Generate traffic, air-quality and accident rows for every (area, hour).
    `times` must include ONE extra leading hour (needed for the lag feature); it is dropped
    from the returned frames.
    """
    times = pd.DatetimeIndex(times)
    A, T = len(areas), len(times)
    rng = np.random.default_rng(seed)
    w = weather_frame(times)
    hour, dow, hol = times.hour.values, times.dayofweek.values, is_holiday(times)
    off = (dow >= 5) | (hol == 1)
    rain = w.rain_mm.values
    ids = areas["id"].values

    # ---------------- traffic
    base = areas.traffic_base.values[:, None]
    boost = 1 + 0.30 * np.minimum(rain, 10) / 10
    idx = 100 * base * _traffic_profile(hour, off)[None, :] * boost[None, :]
    idx = np.clip(idx + _ar(rng, (A, T), 4.0, 0.7), 3, 100)
    cap = np.array([15, 30, 45, 40])[areas.road_code.values][:, None]
    vehicles = np.round(idx * cap * (0.9 + 0.2 * rng.random((A, T))))
    free = np.array([38, 48, 60, 32])[areas.road_code.values][:, None]
    speed = np.clip(free * (1 - idx / 115) ** 1.1 + rng.normal(0, 1.5, (A, T)), 4, 70)

    # ---------------- air quality
    diurnal = 1 + 0.22 * np.cos(2 * np.pi * (hour - 22) / 24) + 0.25 * np.exp(-((hour - 9) / 2.2) ** 2)
    wind_eff = np.clip(1.55 - 0.06 * w.wind_speed.values, 0.6, 1.4)
    rain_eff = 1 - 0.45 * np.minimum(rain, 6) / 6
    hum_eff = 1 + 0.003 * (w.humidity.values - 65)
    season = 1 + 0.22 * np.cos(2 * np.pi * (times.dayofyear.values - 15) / 365)
    env = (diurnal * wind_eff * rain_eff * hum_eff * season)[None, :]
    base_pm = (58 * areas.pollution_base.values + 12 * areas.industrial_index.values)[:, None]
    pm25 = np.clip(base_pm * env * (1 + 0.45 * (idx / 100 - 0.5)) + _ar(rng, (A, T), 3.0, 0.8), 6, 380)
    pm10 = np.clip(pm25 * (1.55 + 0.35 * rng.random((A, T))) + rng.normal(0, 4, (A, T)), 10, 600)
    com = areas.commercial_index.values[:, None]
    ind = areas.industrial_index.values[:, None]
    no2 = np.clip(16 + 0.5 * idx * (0.8 + 0.4 * com) + rng.normal(0, 4, (A, T)), 5, 300)
    so2 = np.clip(5 + 30 * ind * (0.7 + 0.6 * rng.random((A, T))), 2, 300)
    co = np.clip(0.4 + 0.016 * idx + 0.2 * ind + rng.normal(0, 0.08, (A, T)), 0.1, 15)
    sun = np.maximum(0, np.sin(np.pi * (hour - 7) / 11)) * (1 - 0.6 * np.minimum(rain, 5) / 5)
    o3 = np.clip(18 + 45 * sun[None, :] + rng.normal(0, 4, (A, T)), 5, 300)
    aqi = aqi_from_pollutants(pm25, pm10, no2, so2, co, o3)

    # ---------------- accident risk
    vis = w.visibility_km.values[None, :]
    is_night = ((hour >= 19) | (hour < 6)).astype(int)
    hist = areas.accident_hist.values[:, None]
    junction = areas.has_junction.values[:, None]
    score = (0.30 * idx / 100 + 0.15 * np.minimum(rain, 10)[None, :] / 10 + 0.15 * (1 - vis / 10)
             + 0.10 * np.clip(speed - 40, 0, 25) / 25 + 0.15 * is_night[None, :] + 0.10 * junction
             + 0.15 * hist / 50 + _ar(rng, (A, T), 0.02, 0.9) + rng.normal(0, 0.03, (A, T)))
    score = np.clip(score, 0, 1)
    acc_count = rng.poisson(0.5 * score ** 3)

    s = slice(1, None)  # drop the lead hour
    t_out = times[s]

    traffic = _long(
        t_out, ids, traffic_index=np.round(idx[:, s], 1), vehicle_count=vehicles[:, s].astype(int),
        avg_speed=np.round(speed[:, s], 1), prev_traffic_index=np.round(idx[:, :-1], 1),
        is_holiday=hol[s], day_of_week=dow[s], weather=w.weather.values[s],
        rain_mm=rain[s], temperature=w.temperature.values[s])
    traffic["congestion_level"] = [traffic_level(v) for v in traffic["traffic_index"].values]
    traffic = traffic[["timestamp", "location_id", "traffic_index", "vehicle_count", "avg_speed",
                       "congestion_level", "prev_traffic_index", "is_holiday", "day_of_week",
                       "weather", "rain_mm", "temperature"]]

    air = _long(
        t_out, ids, pm25=np.round(pm25[:, s], 1), pm10=np.round(pm10[:, s], 1), co=np.round(co[:, s], 2),
        no2=np.round(no2[:, s], 1), so2=np.round(so2[:, s], 1), o3=np.round(o3[:, s], 1),
        temperature=w.temperature.values[s], humidity=w.humidity.values[s],
        wind_speed=w.wind_speed.values[s], rain_mm=rain[s], traffic_index=np.round(idx[:, s], 1),
        aqi=aqi[:, s])
    air["category"] = [aqi_category(v) for v in air["aqi"].values]

    acc = _long(
        t_out, ids, traffic_index=np.round(idx[:, s], 1), rain_mm=rain[s],
        visibility_km=w.visibility_km.values[s], avg_speed=np.round(speed[:, s], 1),
        is_night=is_night[s], risk_score=np.round(score[:, s], 3), accident_count=acc_count[:, s])
    acc["road_code"] = np.repeat(areas.road_code.values, len(t_out))
    acc["has_junction"] = np.repeat(areas.has_junction.values, len(t_out))
    acc["hist_accidents"] = np.repeat(areas.accident_hist.values, len(t_out))
    acc["risk_level"] = risk_label_from_score(acc["risk_score"].values)
    acc = acc[["timestamp", "location_id", "traffic_index", "road_code", "has_junction", "rain_mm",
               "visibility_km", "avg_speed", "is_night", "hist_accidents", "risk_score",
               "risk_level", "accident_count"]]
    return traffic, air, acc


# ------------------------------------------------------------------------------- electricity
def gen_electricity(times, seed: int = 0) -> pd.DataFrame:
    times = pd.DatetimeIndex(times)
    T = len(times)
    rng = np.random.default_rng(seed)
    w = weather_frame(times)
    h, dow, hol = times.hour.values.astype(float), times.dayofweek.values, is_holiday(times)
    prof = (0.66 + 0.14 * np.exp(-((h - 10) / 2.6) ** 2) + 0.30 * np.exp(-((h - 19.5) / 2.3) ** 2)
            + 0.06 * np.exp(-((h - 14) / 2) ** 2))
    day_f = np.where(hol == 1, 0.90, np.where(dow == 6, 0.92, np.where(dow == 5, 0.96, 1.0)))
    t = w.temperature.values
    temp_f = 1 + 0.02 * np.maximum(0, t - 24) + 0.008 * np.maximum(0, 19 - t)
    noise = lfilter([1.0], [1.0, -0.8], rng.normal(0, 14, T))
    demand = 1400 * prof * day_f * temp_f + noise
    return pd.DataFrame({"timestamp": times, "demand_mw": np.round(demand, 1),
                         "temperature": w.temperature.values, "humidity": w.humidity.values,
                         "is_holiday": hol})


# ------------------------------------------------------------------------------- daily
_TYPE_WATER = {"residential": 1.0, "commercial": 1.1, "IT": 1.15, "industrial": 1.3, "mixed": 1.05}


def gen_water(dates, areas: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    d = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize()
    A, D = len(areas), len(d)
    rng = np.random.default_rng(seed)
    dw = daily_weather(d)
    hol, dow = is_holiday(d), d.dayofweek.values
    typef = areas.area_type.map(_TYPE_WATER).values[:, None]
    pop = areas.population_k.values[:, None]
    f_temp = (1 + 0.014 * (dw.temp_max.values - 26))[None, :]
    f_wk = (1 + 0.05 * (dow >= 5) + 0.02 * hol)[None, :]
    f_rain = (1 - 0.06 * (dw.rain_mm.values > 2))[None, :]
    cons = pop * 0.135 * typef * f_temp * f_wk * f_rain * (1 + 0.025 * rng.normal(size=(A, D)))
    df = pd.DataFrame({
        "date": np.tile(d.date, A), "location_id": np.repeat(areas["id"].values, D),
        "consumption_ml": np.round(cons.reshape(-1), 3), "temp_max": np.tile(dw.temp_max.values, A),
        "rainfall_mm": np.tile(np.round(dw.rain_mm.values, 1), A), "is_holiday": np.tile(hol, A)})
    return df


def gen_waste(dates, areas: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    d = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize()
    A, D = len(areas), len(d)
    rng = np.random.default_rng(seed)
    dw = daily_weather(d)
    hol, fest, dow = is_holiday(d), is_festival(d), d.dayofweek.values
    pop = areas.population_k.values[:, None]
    com = areas.commercial_index.values[:, None]
    f_day = (1 + 0.10 * (dow >= 5) + 0.12 * hol + 0.22 * fest)[None, :]
    f_temp = (1 + 0.02 * (dw.temp_max.values - 26))[None, :]
    f_rain = (1 + 0.05 * (dw.rain_mm.values > 2))[None, :]
    total = pop * 0.10 * (1 + 0.5 * com) * f_day * f_temp * f_rain * (1 + 0.05 * rng.normal(size=(A, D)))
    org = total * np.clip(0.36 + 0.14 * (1 - com) + 0.04 * fest[None, :] + 0.01 * rng.normal(size=(A, D)), .3, .6)
    plas = total * np.clip(0.17 + 0.08 * com + 0.01 * rng.normal(size=(A, D)), .1, .3)
    pap = total * np.clip(0.11 + 0.07 * com + 0.01 * rng.normal(size=(A, D)), .05, .25)
    other = np.maximum(total - org - plas - pap, 0.02 * total)
    total = org + plas + pap + other
    collected = total * (0.90 + 0.10 * rng.random((A, D)))
    r3 = lambda x: np.round(x.reshape(-1), 2)
    return pd.DataFrame({
        "date": np.tile(d.date, A), "location_id": np.repeat(areas["id"].values, D),
        "organic_tons": r3(org), "plastic_tons": r3(plas), "paper_tons": r3(pap), "other_tons": r3(other),
        "total_tons": r3(total), "collected_tons": r3(collected),
        "temp_max": np.tile(dw.temp_max.values, A), "rainfall_mm": np.tile(np.round(dw.rain_mm.values, 1), A),
        "is_holiday": np.tile(hol, A), "is_festival": np.tile(fest, A)})
