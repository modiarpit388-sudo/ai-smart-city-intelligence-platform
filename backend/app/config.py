"""Central configuration. Every value can be overridden with an environment variable."""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)


def _db_uri() -> str:
    uri = os.getenv("DATABASE_URL")
    if not uri:
        return "sqlite:///" + os.path.join(INSTANCE_DIR, "smartcity.db").replace("\\", "/")
    if uri.startswith("postgres://"):  # Heroku/Render style URL
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-city-ai-dev-secret-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))

    MODEL_DIR = os.path.join(INSTANCE_DIR, "models")
    STATIC_DIR = os.path.join(BASE_DIR, "static")  # built React app is served from here

    # How much synthetic history is generated on first start
    HOURLY_HISTORY_DAYS = int(os.getenv("HOURLY_HISTORY_DAYS", "90"))
    DAILY_HISTORY_DAYS = int(os.getenv("DAILY_HISTORY_DAYS", "150"))
    ELECTRICITY_HISTORY_DAYS = int(os.getenv("ELECTRICITY_HISTORY_DAYS", "150"))

    # Optional LLM for the AI City Assistant (answers are grounded in DB + ML output)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    CITY_NAME = "Bengaluru"
