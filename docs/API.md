# REST API (all under `/api`, JSON, `Authorization: Bearer <JWT>` unless public)

| Method & path | Roles | Description |
|---|---|---|
| `GET /health` | public | health check |
| `GET /auth/areas` | public | localities for the registration form |
| `POST /auth/register` | public | step 1 of registration `{name,email,password,area_id}` → emails a 6-digit OTP, returns `202 {verification_required,email,expires_in,resend_in}` (no account yet) |
| `POST /auth/verify-otp` | public | step 2 `{email,otp}` → creates the citizen account, returns `{token,user}`. Errors: `otp_invalid`, `otp_expired`, `otp_locked` |
| `POST /auth/logout` | public | signs out: cancels this login's session key (`jti`) so the token can never be reused |
| `POST /auth/resend-otp` | public | `{email}` → new OTP (60 s cooldown, `429` with `retry_after` otherwise) |
| `POST /auth/login` | public | `{email,password}` → `{token,user}` |
| `GET/PUT /auth/me` | any | profile, change home area / name / password |
| `GET /city/areas` | any | list of localities |
| `GET /city/overview` | any | KPIs + per-area traffic/AQI/water/waste/accident |
| `GET /city/area/<id>` | any | one-locality snapshot + alerts |
| `GET /predict/traffic?area_id=` | any | current, 12-h forecast, ranking, city curve |
| `GET /predict/aqi?area_id=` | any | AQI, pollutants, 24-h forecast, tomorrow periods |
| `GET /predict/accident?area_id=` | any | risk %, level, factors, forecast, importance |
| `POST /predict/accident/custom` | any | what-if `{area_id,hour,traffic_index,rain_mm,visibility_km}` |
| `GET /predict/electricity` | any | demand now/today/tomorrow/peak + 48-h forecast |
| `GET /predict/water?area_id=` | any | today/tomorrow/%, 7-day forecast, area table |
| `GET /predict/waste?area_id=` | any | tons, category split, high zones, collection plan |
| `POST /complaints/analyze` | any | NLP preview `{text}` |
| `POST /complaints` | citizen, admin | file a complaint (auto-analysed & routed) |
| `GET /complaints?status=&priority=&category=&sort=priority` | any (scoped) | list |
| `GET /complaints/<id>` | any (scoped) | detail + timeline |
| `PUT /complaints/<id>/status` | authority, admin | `{status,note}` |
| `GET /complaints/stats` · `/complaints/clusters` | scoped / staff | statistics, K-Means groups |
| `GET /alerts` · `POST /alerts/refresh` | any / staff | AI alerts |
| `GET /notifications` · `POST /notifications/read` | any | user notifications |
| `POST /assistant/chat` | any | `{message}` → grounded answer |
| `GET /department/dashboard[?dept=slug]` | authority, admin | department dashboard |
| `GET /reports` · `GET /reports/<kind>?period=&format=csv` | staff | reports |
| `GET/POST/PUT /admin/users` | admin | user management |
| `GET /admin/datasets` · `POST /admin/datasets/ingest` | admin | dataset summary, ingest |
| `GET /admin/datasets/<table>/export` · `POST …/import` | admin | CSV export / import |
| `GET /admin/models` · `POST /admin/models/retrain` · `GET /admin/models/status` | admin | model registry & training |
| `GET /admin/analytics` | admin | system counters |
