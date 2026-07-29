import logging

from db.database import get_pool
from db.models import get_sheet_id as _db_get_sheet_id

logger = logging.getLogger(__name__)

_allowed_users: dict[int, str] = {}
_user_sheet_ids: dict[int, int] = {}
_user_names: dict[int, str] = {}


async def reload_users() -> None:
    global _allowed_users, _user_sheet_ids, _user_names
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT tele_user_id, name, role, sheet_id FROM telegram_users"
        )
    _allowed_users = {r["tele_user_id"]: r["role"] for r in rows}
    _user_names = {r["tele_user_id"]: r["name"] for r in rows}
    _user_sheet_ids = {
        r["tele_user_id"]: r["sheet_id"]
        for r in rows
        if r["sheet_id"] is not None
    }
    logger.info("Loaded %d authorized user(s)", len(_allowed_users))


async def is_authorized(tele_user_id: int) -> bool:
    if tele_user_id in _allowed_users:
        return True
    await reload_users()
    return tele_user_id in _allowed_users


def is_admin(tele_user_id: int) -> bool:
    return _allowed_users.get(tele_user_id) == "admin"


async def get_sheet_id(tele_user_id: int) -> int | None:
    sid = _user_sheet_ids.get(tele_user_id)
    if sid is not None:
        return sid
    sid = await _db_get_sheet_id(tele_user_id)
    if sid is not None:
        _user_sheet_ids[tele_user_id] = sid
    return sid
