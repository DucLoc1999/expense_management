import os
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")
BOT_LOCALE: str = os.getenv("BOT_LOCALE", "vi")
DATABASE_URL: str = _require("DATABASE_URL")
DB_SCHEMA: str = os.getenv("DB_SCHEMA", "public")
EXPERT_MAX_BILLS_FOR_AI: int = int(os.getenv("EXPERT_MAX_BILLS_FOR_AI", "50"))

ENV_MODE: str = os.getenv("ENV_MODE", "polling").strip().lower()
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "").strip()
PORT: int = int(os.getenv("PORT", "8443"))
