import logging
from dataclasses import dataclass
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

import config
from db.models import get_sheet_id, set_sheet_id

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

HEADERS = ["Date", "Item", "Money", "Shop", "Category", "Payment Source", "Notes"]


@dataclass
class OrderRow:
    date: str
    name: str
    money: int
    shop: str
    category: str
    payment_source: str = "shopee"
    notes: str = ""


def _get_client() -> gspread.Client:
    creds_path = Path(config.GOOGLE_SERVICE_ACCOUNT_FILE)
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    return gspread.authorize(creds)


async def _get_worksheet(tele_user_id: int) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_ID)
    tab_name = str(tele_user_id)

    sheet_id = await get_sheet_id(tele_user_id)

    if sheet_id is not None:
        try:
            return spreadsheet.get_worksheet_by_id(sheet_id)
        except gspread.WorksheetNotFound:
            logger.warning("Sheet tab %s (id=%s) deleted, recreating", tab_name, sheet_id)

    try:
        ws = spreadsheet.worksheet(tab_name)
        sheet_id = ws.id
        await set_sheet_id(tele_user_id, sheet_id)
        return ws
    except gspread.WorksheetNotFound:
        pass

    try:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(HEADERS))
    except gspread.exceptions.APIError:
        ws = spreadsheet.worksheet(tab_name)

    sheet_id = ws.id
    await set_sheet_id(tele_user_id, sheet_id)
    return ws


async def append_orders(rows: list[OrderRow], tele_user_id: int) -> tuple[bool, str | None]:
    """Append rows to sheet. Returns (success, error_message)."""
    if not rows:
        return True, None
    try:
        ws = await _get_worksheet(tele_user_id)
        existing = ws.get_all_values()
        if not existing:
            ws.append_row(HEADERS)
        data = [
            [r.date, r.name, r.money, r.shop, r.category, r.payment_source, r.notes]
            for r in rows
        ]
        ws.append_rows(data, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        logger.error("Sheets append failed: %s", e)
        return False, str(e)


async def append_one(row: OrderRow, tele_user_id: int) -> tuple[bool, str | None]:
    return await append_orders([row], tele_user_id)
