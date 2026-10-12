# Architecture

## 1. Overall architecture

```
   Citizen / Authority / Admin (browser)
                │  HTTPS + JWT
                ▼
   ┌──────────────────────────────┐
   │ React SPA (Vite)             │  dashboards · Leaflet map · Recharts · Framer Motion
   └──────────────┬───────────────┘
                  │ REST /api/*
                  ▼
   ┌──────────────────────────────┐
   │ Flask API                    │  routes → services → ml
   │  auth · city · complaints    │
   │  misc · admin                │
   └───┬──────────┬───────────┬───┘
       ▼          ▼           ▼
   ┌────────┐ ┌─────────┐ ┌─────────┐
   │  SQL   │ │ ML      │ │ NLP     │
   │ DB     │ │ models  │ │ engine  │
   └───▲────┘ └────▲────┘ └─────────┘
       │           │ joblib files (instance/models)
   ┌───┴───────────┴───┐
   │ Ingestion         │  simulators today · IoT / open-data connectors tomorrow
   │ + scheduler       │
   └───────────────────┘
```

Request flow example (`GET /api/predict/traffic?area_id=1`):
`routes/city.py` → `services/insights.traffic_payload` → `ml/forecast.traffic_forecast`
→ loads model bundle from `ml/registry` → recursive prediction using `simulation/weather` → JSON.

## 2. Data flow & the ML life-cycle

1. **Ingest** – `services/ingest.py` writes hourly/daily readings to the DB (`ensure_data_current`), on start and every 5 min.
2. **Train** – `ml/pipelines.py` reads the tables with pandas, builds features, `ml/registry.py` trains several candidates
   on a **time-based split**, scores them, refits the best on all data and saves it.
3. **Register** – every candidate + metrics is stored in `ml_models` / `model_metrics` (visible in Admin → ML Models).
4. **Predict** – `ml/forecast.py` recursively forecasts; results are cached per hour and snapshotted in `predictions`.
5. **Act** – `services/alerts.py` converts forecasts into alerts → `alerts` + `notifications`.

## 3. Forecasting design

* **Recursive multi-step**: step *h* uses the prediction of step *h-1* as its "previous value" feature.
* **Weather service** (`simulation/weather.py`) is a deterministic function of time, so history and forecast use the same code.
* **Cascading models**: traffic forecast → (AQI model, accident model).
* **AQI** is computed from pollutants with the Indian CPCB sub-index method (`utils.aqi_from_pollutants`).
* **Accident risk %** = probability-weighted class score `0.15·P(low)+0.55·P(medium)+0.95·P(high)`.

## 4. NLP pipeline (`ml/nlp.py`)

```
text ─ TF-IDF(1-2 grams) ─┬─ category classifier (9 classes)
                          ├─ priority classifier (LOW/MEDIUM/HIGH) + safety-keyword rules
     ─ lexicon sentiment ─┤
     ─ TF-IDF keywords ───┤
     ─ gazetteer locality ┘
     ─ TF-IDF + K-Means → complaint group (recurring problems)
```
Department routing: category → department (`complaint_categories.department_id`).

## 5. Database schema (ER overview)

```
departments ─┬─< users >─┬─ citizens        users(role: citizen|authority|admin)
             │           └─ admins
             ├─< complaint_categories ─< complaints >─< complaint_updates
             └─< alerts >─< notifications >─ users

locations ─┬─< traffic_data      ─┬ accident_data     ─┬ air_quality
           ├─< water_consumption  ├ waste_data         └ electricity_data (city level)
           └─< predictions >─ ml_models ─< model_metrics
```

| Table | Purpose |
|---|---|
| users / citizens / admins / departments | identity, roles, department membership |
| locations | 20 localities: lat/lng, population, area & road type, baselines |
| traffic_data | hourly index, vehicles, speed, level, previous index, weather |
| accident_data | hourly risk features + label (`LOW/MEDIUM/HIGH`) |
| air_quality | hourly pollutants, weather, AQI, category |
| electricity_data | hourly city demand (MW) |
| water_consumption | daily ML per locality |
| waste_data | daily tons per locality + organic/plastic/paper/other |
| complaint_categories / complaints / complaint_updates | complaint workflow + NLP output + timeline |
| predictions | latest forecast snapshot |
| alerts / notifications | AI alerts and per-user notifications |
| ml_models / model_metrics | model registry and metrics |

## 6. Security

* Passwords hashed (Werkzeug PBKDF2). JWT (HS256) with expiry; `Authorization: Bearer <token>`.
* `@auth_required(role…)` decorator enforces RBAC on every route; authorities only see their department's complaints,
  citizens only their own.
* All SQL goes through SQLAlchemy / bound parameters. CSV import validates column names.
