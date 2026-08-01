import logging

from db.database import get_pool

logger = logging.getLogger(__name__)

_allowed_users: dict[int, str] = {}
_user_names: dict[int, str] = {}


async def reload_users() -> None:
    global _allowed_users, _user_names
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT tele_user_id, name, role FROM telegram_users"
        )
    _allowed_users = {r["tele_user_id"]: r["role"] for r in rows}
    _user_names = {r["tele_user_id"]: r["name"] for r in rows}
    logger.info("Loaded %d authorized user(s)", len(_allowed_users))


async def is_authorized(tele_user_id: int) -> bool:
    if tele_user_id in _allowed_users:
        return True
    await reload_users()
    return tele_user_id in _allowed_users


def is_admin(tele_user_id: int) -> bool:
    return _allowed_users.get(tele_user_id) == "admin"
