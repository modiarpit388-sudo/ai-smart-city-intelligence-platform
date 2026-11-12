"""Central configuration. Every value can be overridden with an environment variable."""
import os

ENV_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
ENV_FILE_FOUND = os.path.isfile(ENV_FILE)
try:  # load backend/.env (override=True so a stray Windows environment variable can't beat the file)
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE, override=True, encoding="utf-8-sig")
except ImportError:
    print("\n  ⚠ python-dotenv is not installed, so backend/.env is IGNORED. Run:  pip install python-dotenv\n")

def _str(name: str, default: str = "") -> str:
    """Read a text env var, trimming spaces and accidental surrounding quotes."""
    return os.getenv(name, default).strip().strip("\"'").strip()


def _int(name: str, default: int) -> int:
    """Read an integer env var; if the value is not a number, warn and use the default instead of crashing."""
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        print(f"\n  ⚠ .env problem: {name} must be a number but is not (check that the values are on the "
              f"correct lines). Using {default}.\n")
        return default


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

    # ---- Login sessions ------------------------------------------------------------
    # Every login token carries this key. Change SESSION_KEY in .env (any text) to sign EVERYONE out at once.
    SESSION_KEY = _str("SESSION_KEY") or "v1"

    # ---- Email verification (OTP) ------------------------------------------------
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = _int("OTP_EXPIRY_MINUTES", 10)
    OTP_MAX_ATTEMPTS = _int("OTP_MAX_ATTEMPTS", 5)        # wrong guesses before the code is burned
    OTP_RESEND_SECONDS = _int("OTP_RESEND_SECONDS", 60)   # cooldown between sends

    # Delivery method: "brevo" (HTTPS API, recommended - reaches any inbox reliably) or "smtp" (e.g. Gmail).
    BREVO_API_KEY = _str("BREVO_API_KEY")
    BREVO_API_URL = _str("BREVO_API_URL") or "https://api.brevo.com/v3/smtp/email"
    MAIL_PROVIDER = (_str("MAIL_PROVIDER") or ("brevo" if _str("BREVO_API_KEY") else "smtp")).lower()

    # SMTP. If SMTP_HOST is empty the OTP is printed to the server console instead (dev mode).
    SMTP_HOST = _str("SMTP_HOST")
    SMTP_PORT = _int("SMTP_PORT", 587)
    SMTP_USER = _str("SMTP_USER")
    SMTP_PASSWORD = _str("SMTP_PASSWORD").replace(" ", "")  # Google shows app passwords with spaces - they are not part of it
    SMTP_DEBUG = _str("SMTP_DEBUG").lower() in ("1", "true", "yes")  # print the full SMTP conversation
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")    # STARTTLS (port 587)
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")  # True for port 465
    MAIL_FROM = _str("MAIL_FROM") or _str("SMTP_USER") or "no-reply@smartcity.ai"

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
