import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")
GOOGLE_SHEETS_ID: str = _require("GOOGLE_SHEETS_ID")
GOOGLE_SERVICE_ACCOUNT_FILE: str = _require("GOOGLE_SERVICE_ACCOUNT_FILE")
ALLOWED_USER_ID: int = int(_require("ALLOWED_USER_ID"))
SHEET_TAB_NAME: str = os.getenv("SHEET_TAB_NAME", "Orders")
DB_PATH: str = os.getenv("DB_PATH", "data/expense.db")
