# Viva / demo guide

## 60-second pitch
"An AI-powered smart-city decision-support platform. Six ML models forecast traffic, accident risk, air quality,
electricity, water and waste for 20 Bengaluru localities, an NLP engine categorises and routes citizen complaints,
and three role-based portals (citizen, department, admin) sit on one Flask + React + SQL stack."

## Suggested demo order (5 minutes)
1. Login page → *Admin* one-click. Point out the live ticker and KPI cards.
2. **Command Center** → switch map layers → click *Silk Board*.
3. **Traffic** → hour chips + forecast chart → explain recursive forecasting.
4. **Accident Risk** → gauge, factors, drag the *what-if* sliders (night + rain + heavy traffic → HIGH).
5. **Complaints** (login as citizen) → type *"Live wire fallen near Silk Board, very dangerous"* → show live NLP analysis → submit.
6. Login as *Authority* (Traffic) → work-queue → change status → citizen gets a notification.
7. **Admin → ML Models** → algorithm comparison, confusion matrix, feature importance → *Retrain*.
8. Open the **AI assistant** → "Which areas have the highest waste generation?"

## Questions examiners ask
**Why several algorithms per module?** To compare objectively; the registry stores every candidate's metrics and activates the best (lowest RMSE / highest F1).

**How do you avoid data leakage?** Time-based split for time series; lag features only use the past; NLP is tested on unseen templates.

**How does multi-step forecasting work?** Recursively – the predicted value becomes the *previous value* input of the next step.

**Why not LSTM?** Gradient-boosted trees with lag features are strong on tabular time series with ~40 k rows, train in seconds and
are explainable. LSTM/GRU can be added as another candidate in `ml/registry.py`.

**Is the data real?** It is simulated with realistic patterns (rush hours, monsoon, CPCB AQI formula, festivals). The pipeline is
data-source agnostic: import CSVs or add connectors and retrain.

**How is AQI computed?** CPCB (India) method – piece-wise linear sub-index per pollutant; overall AQI = max sub-index.

**How is accident risk % defined?** Probability-weighted class score of the classifier (0.15/0.55/0.95 for LOW/MED/HIGH).

**How does the assistant avoid hallucination?** It retrieves numbers from the DB/ML services first; the optional LLM only rephrases and
is instructed to use those facts only.

**How is security handled?** Hashed passwords, JWT with expiry, role decorators on every endpoint, scoped queries, parameterised SQL.

**How would it scale?** Move to PostgreSQL + TimescaleDB, stream sensor data via MQTT/Kafka, schedule training with Celery/Airflow,
serve models from a separate inference service, add Redis cache.

**Limitations (be honest!)** Synthetic data; complaint corpus is template-generated so real-world accuracy would be lower until trained on
real complaints; single-city; no real-time sensor hardware.
