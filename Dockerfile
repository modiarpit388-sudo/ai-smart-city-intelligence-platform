# ---------- stage 1: build the React app ----------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# vite.config.js writes to ../backend/static
RUN mkdir -p /backend && npm run build

# ---------- stage 2: Flask + ML ----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary
COPY backend/ .
COPY --from=web /backend/static ./static
EXPOSE 5000
# one worker + threads: the app keeps trained models in memory and runs a small scheduler thread
CMD ["gunicorn", "-w", "1", "--threads", "8", "--timeout", "300", "-b", "0.0.0.0:5000", "wsgi:app"]
