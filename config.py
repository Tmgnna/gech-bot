"""Environment-based configuration for Car Equb Bot."""
import os
from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        raise RuntimeError(f"{name} must be an integer")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_GROUP_ID = _int("ADMIN_GROUP_ID", 0)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@support").strip()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook").strip() or "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
HOST = os.getenv("HOST", "0.0.0.0").strip()
PORT = _int("PORT", 8080)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "equb.db")
HOLD_MINUTES = max(1, _int("HOLD_MINUTES", 15))
SESSION_TTL_SECONDS = max(300, _int("SESSION_TTL_SECONDS", 8 * 60 * 60))
LOGIN_MAX_ATTEMPTS = max(3, _int("LOGIN_MAX_ATTEMPTS", 5))
LOGIN_LOCK_SECONDS = max(30, _int("LOGIN_LOCK_SECONDS", 300))
COOKIE_SECURE = _bool("COOKIE_SECURE", False)  # Set to 1 behind HTTPS in production.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
USE_WEBHOOK = bool(WEBHOOK_URL and BOT_TOKEN)


def validate_settings() -> None:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not ADMIN_PASSWORD:
        missing.append("ADMIN_PASSWORD")
    if len(SECRET_KEY) < 32:
        missing.append("SECRET_KEY (at least 32 characters)")
    if USE_WEBHOOK and not WEBHOOK_SECRET:
        missing.append("WEBHOOK_SECRET (when WEBHOOK_URL is set)")
    if missing:
        raise SystemExit("Missing/invalid required settings: " + ", ".join(missing) + ". Copy .env.example to .env and configure it.")
