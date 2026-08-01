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
