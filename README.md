# 🏙️ AI Smart City Intelligence Platform

> Designed by **ARPIT MODI**

A complete full-stack **AI + ML + NLP** web application for urban decision support (Bengaluru, 20 localities).

> *An AI-powered Smart City Intelligence and Decision Support Platform that integrates multiple machine-learning
> models for urban traffic, accident risk, air quality, electricity demand, water consumption, waste generation and
> citizen-complaint analytics through a centralized web-based dashboard.*

| Layer | Technology |
|---|---|
| Frontend | React 18 · Vite · Recharts · Leaflet · Framer Motion · custom "city at night" design system |
| Backend | Python 3.10+ · Flask · SQLAlchemy · JWT (PyJWT) · role-based access control |
| ML / AI | pandas · NumPy · scikit-learn · XGBoost · TF-IDF NLP · K-Means |
| Database | SQLite by default → **PostgreSQL** with one env variable |
| Deployment | Docker + docker-compose · gunicorn |

---

## 🚀 Quick start

### Option A — one command (Linux / macOS)
```bash
./start.sh
```
### Option A — one command (Windows)
Double-click **`start.bat`**

### Option B — manual
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```
Open **http://localhost:5000**.

> **First start takes ~1–2 minutes**: the platform creates the database, generates realistic city data,
> trains all 9 ML models and builds the first alerts. Every later start is instant.
> The React app is already built into `backend/static`, so **Node.js is not needed to run it**.

### Option C — Docker (with PostgreSQL)
```bash
docker compose up --build
```

### Front-end development mode (hot reload)
```bash
cd frontend && npm install && npm run dev       # http://localhost:5173  (proxies /api to :5000)
npm run build                                   # rebuilds into backend/static
```

---

## 🔑 Demo accounts (click the one-click buttons on the login page)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@smartcity.ai` | `Admin@123` |
| Citizen (HSR Layout) | `citizen@smartcity.ai` | `Citizen@123` |
| Authority – Traffic | `traffic@smartcity.ai` | `Authority@123` |
| Authority – Pollution | `pollution@smartcity.ai` | `Authority@123` |
| Authority – Water | `water@smartcity.ai` | `Authority@123` |
| Authority – Electricity | `electricity@smartcity.ai` | `Authority@123` |
| Authority – Waste | `waste@smartcity.ai` | `Authority@123` |

Citizens can also **register** themselves (the email is verified with a 6-digit OTP – see `.env.example` for SMTP setup; without SMTP the code is printed in the server console). Admins create authority accounts (Admin → Users).

---

## ✅ Feature checklist (maps 1-to-1 to the project brief)

| # | Module | What you get |
|---|---|---|
| 1 | 🚦 **Traffic prediction** | 12-hour forecast per locality (`5 PM → Medium … 7 PM → High`), hotspot ranking, city-wide curve, weather-aware |
| 2 | 🚨 **Accident risk** | LOW / MEDIUM / HIGH classifier, animated risk gauge, "main factors", 12-h risk forecast, **what-if simulator**, feature importance |
| 3 | 🌫️ **Air quality** | CPCB AQI from PM2.5/PM10/NO₂/SO₂/CO/O₃, 24-h forecast, tomorrow *Morning/Afternoon/Evening/Night*, pollutant tiles |
| 4 | ⚡ **Electricity demand** | Hourly load forecast, today/tomorrow/peak demand + peak time, load by locality |
| 5 | 💧 **Water consumption** | Area-wise today/tomorrow/% change, 7-day forecast, status NORMAL/HIGH/LOW |
| 6 | 🗑️ **Waste generation** | Organic/Plastic/Paper/Other split, high-waste areas, **collection schedule** with trucks needed |
| 7 | 📢 **Complaint NLP** | Category, priority, sentiment, keywords, location extraction, department routing, K-Means complaint groups, live analysis while typing |
| 8 | 🗺️ **Interactive map** | Leaflet map, 5 switchable layers (traffic/AQI/accident/water/waste), pulsing hotspots, click for full locality card |
| 9 | 📊 **Admin dashboard** | KPI cards, map, alerts, forecasts, hotspots |
| 10 | 👤 **Citizen portal** | "My Area" card, complaints + tracking timeline, alerts, notifications |
| 11 | 👨‍💼 **Authority portals** | Separate dashboard per department (traffic / pollution / water / electricity / waste) + complaint work-queue |
| 12 | 🔔 **AI alert system** | Rule engine on top of forecasts, alert ticker, notifications to departments and affected citizens |
| 13 | 🤖 **AI City Assistant** | Floating chat; answers come from **your DB + ML output** (never invented). Optional LLM rewrite via `ANTHROPIC_API_KEY` |
| 14 | 📈 **Analytics & reports** | Traffic / AQI / accident / electricity / water / waste / complaints / model accuracy — daily, weekly, monthly, yearly + CSV + print |
| 15 | 🧠 **ML model management** | Compare algorithms, metrics (RMSE/MAE/R², Accuracy/Precision/Recall/F1), confusion matrix, actual-vs-predicted, feature importance, **retrain from the UI** |
| 16 | 🗄️ **Database** | All tables from the brief (see `docs/ARCHITECTURE.md`) |
| 17 | 🔐 **Login & roles** | JWT auth, Citizen / Authority / Admin, user management, dataset management |
| 18 | 🧪 **ML zoo** | Linear/Ridge, Random Forest, Gradient Boosting, XGBoost, Logistic Regression, Linear SVM, Naive Bayes, TF-IDF, K-Means |
| 19 | 🛠️ **Stack** | Flask + React + SQL DB + scikit-learn/XGBoost + Leaflet + Recharts + Docker |

Animated, themed UI: night-city skyline with driving cars, blinking windows and a patrol drone, live IoT-node network
canvas, radar loaders, count-up KPIs, animated gauges, pulsing map hotspots, scrolling alert ticker, animated page transitions.

---

## 🧠 How the AI works

| Module | Task | Candidate algorithms (best is auto-selected & stored) | Key inputs |
|---|---|---|---|
| Traffic | Regression / time-series | Linear, Random Forest, Gradient Boosting, XGBoost | hour (sin/cos), weekday, holiday, rain, temperature, road type, area base, **previous-hour traffic** |
| Accident | Classification | Logistic, Random Forest, Gradient Boosting, XGBoost | traffic density, rain, visibility, speed, night, junction, historical accidents |
| AQI | Regression / time-series | same | weather, hour, area, **traffic forecast**, previous-hour AQI |
| Electricity | Time series | same | hour, day, month, holiday, temperature, humidity, lag-1h, lag-24h |
| Water | Regression | same | population, area type, temperature, rainfall, weekday, holiday, lag-1d, lag-7d |
| Waste | Regression | same | population, commercial activity, festival/holiday, weather, lag-1d, lag-7d |
| Complaint category | NLP classification | TF-IDF + Logistic / Linear SVM / Naive Bayes | complaint text |
| Complaint priority | NLP classification (+ safety-keyword rules) | same | complaint text |
| Complaint groups | Clustering | TF-IDF + K-Means (K = 9) | complaint text |

**Honest evaluation.** Regression models use a *time-based split* (oldest data trains, newest 14–21 days test) so there
is no future leakage. NLP models are tested on complaint templates *never seen in training*. Forecasts beyond one step are
**recursive**: hour *t+1*'s prediction is fed back as the "previous value" for hour *t+2*.

**Modules feed each other** – the AQI and accident models consume the *traffic forecast*, and all of them consume the
weather forecast — like a real integrated smart-city stack.

Typical results on the shipped synthetic data (they vary slightly per run):
Traffic R² ≈ 0.96 · AQI R² ≈ 0.88 · Electricity R² ≈ 0.98 · Water R² ≈ 0.99 · Waste R² ≈ 0.95 ·
Accident accuracy ≈ 85 % · Complaint category F1 ≈ 0.8 · priority F1 ≈ 0.83.

### About the data
No open dataset covers all of these Bengaluru sensors, so the platform ships **realistic simulators**
(`backend/app/simulation/`): rush-hour profiles, deterministic weather, the official CPCB AQI formula, AC-driven electricity
load, festival-driven waste, etc. The data is regenerated **relative to "now"**, and a background scheduler appends the
newest hour automatically, so the dashboard is always live.
**To use real data:** *Admin → Datasets → Import CSV* (same column names as the tables), then *Admin → ML Models → Retrain all*.
Or replace the generators with connectors to your sensors / open-data APIs — the ML layer only reads the database.

---

## 🗂️ Project structure

```
smart-city-ai/
├── backend/
│   ├── run.py · wsgi.py · manage.py         entry points / CLI (init, train, ingest, reset)
│   ├── requirements.txt
│   ├── static/                              built React app (served by Flask)
│   └── app/
│       ├── models.py                        SQLAlchemy schema (all tables)
│       ├── auth.py                          JWT + role decorators
│       ├── seed.py                          departments, categories, localities, demo users, sample complaints
│       ├── simulation/                      areas, weather, holiday calendar, data generators, complaint corpus
│       ├── ml/
│       │   ├── registry.py                  train → compare → select → persist (joblib) → metrics tables
│       │   ├── pipelines.py                 feature engineering + training for 6 numeric modules
│       │   ├── nlp.py                       complaint NLP (category, priority, sentiment, keywords, location, clusters)
│       │   ├── forecast.py                  recursive multi-step forecasting
│       │   └── trainer.py                   orchestration + background retraining
│       ├── services/                        ingest · insights · alerts · assistant · reports
│       └── routes/                          auth · city/predict · complaints · misc · admin
├── frontend/                                React + Vite source (pages/, components/, styles.css)
├── docs/                                    ARCHITECTURE.md · API.md · VIVA_GUIDE.md
├── Dockerfile · docker-compose.yml · start.sh · start.bat · .env.example
```

## 🔧 Maintenance commands
```bash
cd backend
python manage.py init      # create tables, seed, ingest, train (idempotent)
python manage.py train     # retrain every model
python manage.py ingest    # catch data up to the current hour
python manage.py reset     # wipe DB + models and rebuild everything
```

## 🔒 Production notes
* Set a strong `SECRET_KEY`; change or delete the demo accounts.
* Use PostgreSQL (`DATABASE_URL`) and run with gunicorn (`wsgi.py`) — the Docker image already does.
* Run **one** gunicorn worker (models are cached in memory and a small scheduler thread runs inside the process).
* Map tiles come from CARTO/OpenStreetMap, so the browser needs internet access for the basemap.

## 🧩 Ideas to extend
LSTM forecasting (TensorFlow/PyTorch) as an extra candidate in `ml/registry.py`; real IoT/MQTT ingestion; SHAP explanations;
email/SMS alerts; PDF report export; multilingual complaint NLP (Kannada/Hindi); geo-clustering of complaints.

*Built as an MCA-level final-year project — see `docs/VIVA_GUIDE.md` for the questions examiners usually ask.*
