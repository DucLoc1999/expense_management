import logging

import asyncpg
import config

from db import migrate

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        schema = config.DB_SCHEMA

        async def _init(conn: asyncpg.Connection) -> None:
            if schema != "public":
                await conn.execute(f'SET search_path TO "{schema}"')

        _pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=2, max_size=10, init=_init)
    return _pool


async def get_db() -> asyncpg.Connection:
    pool = await get_pool()
    return await pool.acquire()


async def release_db(conn: asyncpg.Connection) -> None:
    pool = await get_pool()
    await pool.release(conn)


async def run_migrations() -> None:
    pool = await get_pool()
    await migrate.auto_baseline_if_needed(pool)
    versions_applied = await migrate.run_all(pool)
    if versions_applied:
        logger.info("Applied migrations: %s", versions_applied)
    else:
        logger.info("No pending migrations")


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
