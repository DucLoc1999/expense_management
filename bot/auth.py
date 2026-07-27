import logging

from db.database import get_pool

logger = logging.getLogger(__name__)

_allowed_users: set[int] = set()


async def load_users() -> None:
    global _allowed_users
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT tele_user_id FROM telegram_users")
    _allowed_users = {r["tele_user_id"] for r in rows}
    logger.info("Loaded %d authorized user(s)", len(_allowed_users))


def is_authorized(tele_user_id: int) -> bool:
    return tele_user_id in _allowed_users
