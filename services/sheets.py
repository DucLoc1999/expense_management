import logging
from dataclasses import dataclass
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

HEADERS = ["Date", "Item", "Quantity", "Price", "Money", "Shop", "Category", "Payment Source", "Notes"]
SHEET_TAB = "Orders"


@dataclass
class OrderRow:
    date: str
    name: str
    quantity: int
    price: int
    money: int
    shop: str
    category: str
    payment_source: str = "shopee"
    notes: str = ""


def _get_client() -> gspread.Client:
    creds_path = Path(config.GOOGLE_SERVICE_ACCOUNT_FILE)
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_ID)
    try:
        ws = spreadsheet.worksheet(SHEET_TAB)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=SHEET_TAB, rows=1000, cols=len(HEADERS))
    return ws


async def append_orders(rows: list[OrderRow]) -> tuple[bool, str | None]:
    """Append rows to sheet. Returns (success, error_message)."""
    if not rows:
        return True, None
    try:
        ws = _get_worksheet()
        existing = ws.get_all_values()
        if not existing:
            ws.append_row(HEADERS)
        data = [
            [r.date, r.name, r.quantity, r.price, r.money, r.shop, r.category, r.payment_source, r.notes]
            for r in rows
        ]
        ws.append_rows(data, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        logger.error("Sheets append failed: %s", e)
        return False, str(e)


async def append_one(row: OrderRow) -> tuple[bool, str | None]:
    return await append_orders([row])
