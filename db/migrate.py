import logging
import os
import re
from pathlib import Path
from typing import NamedTuple

import asyncpg

import config

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.getenv("MIGRATIONS_DIR", str(Path(__file__).resolve().parent.parent / "migrations"))

_MIGRATION_PATTERN = re.compile(r"^(\d{3})_(.+)\.sql$")
_SEPARATOR = "-- migrate:down"


class Migration(NamedTuple):
    version: int
    name: str
    up_sql: str
    down_sql: str


async def ensure_table(conn: asyncpg.Connection) -> None:
    schema = config.DB_SCHEMA
    if schema != "public":
        await conn.execute(f'SET search_path TO "{schema}"')
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)


async def applied(conn: asyncpg.Connection) -> set[int]:
    rows = await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
    return {r["version"] for r in rows}


async def pending(conn: asyncpg.Connection) -> list[Migration]:
    migrations = _discover()
    applied_versions = await applied(conn)
    return [m for m in migrations if m.version not in applied_versions]


async def run_all(pool: asyncpg.Pool) -> list[int]:
    migrations = _discover()
    if not migrations:
        logger.info("No migration files found in %s", MIGRATIONS_DIR)
        return []

    async with pool.acquire() as conn:
        await ensure_table(conn)
        applied_versions = await applied(conn)
        to_run = [m for m in migrations if m.version not in applied_versions]

        if not to_run:
            logger.info("All migrations already applied")
            return []

        applied_versions_list = []
        for m in to_run:
            async with conn.transaction():
                logger.info("Applying migration %s: %s", f"{m.version:03d}", m.name)
                await conn.execute(m.up_sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES ($1, $2)",
                    m.version,
                    m.name,
                )
            applied_versions_list.append(m.version)
            logger.info("Applied migration %s: %s", f"{m.version:03d}", m.name)

    return applied_versions_list


async def rollback(pool: asyncpg.Pool, steps: int = 1) -> list[int]:
    migrations = _discover()
    mig_map = {m.version: m for m in migrations}

    async with pool.acquire() as conn:
        await ensure_table(conn)
        rows = await conn.fetch(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT $1",
            steps,
        )

        if not rows:
            logger.info("No migrations to rollback")
            return []

        rolled_back = []
        for row in rows:
            ver = row["version"]
            m = mig_map.get(ver)
            if m is None:
                logger.warning("Migration file %s not found, skipping rollback", f"{ver:03d}")
                continue
            async with conn.transaction():
                logger.info("Rolling back migration %s: %s", f"{ver:03d}", m.name)
                await conn.execute(m.down_sql)
                await conn.execute("DELETE FROM schema_migrations WHERE version = $1", ver)
            rolled_back.append(ver)
            logger.info("Rolled back migration %s: %s", f"{ver:03d}", m.name)

    return rolled_back


async def baseline(pool: asyncpg.Pool) -> list[int]:
    migrations = _discover()

    async with pool.acquire() as conn:
        await ensure_table(conn)
        applied_versions = await applied(conn)
        baselined = []
        for m in migrations:
            if m.version not in applied_versions:
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES ($1, $2)",
                    m.version,
                    m.name,
                )
                baselined.append(m.version)
                logger.info("Baselined migration %s: %s", f"{m.version:03d}", m.name)

    return baselined


async def auto_baseline_if_needed(pool: asyncpg.Pool) -> bool:
    async with pool.acquire() as conn:
        has_categories = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'categories')"
        )
        has_schema_migrations = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'schema_migrations')"
        )

        if has_categories and not has_schema_migrations:
            logger.info("Existing database detected — auto-baselining migrations")
            await baseline(pool)
            return True

    return False


async def status(pool: asyncpg.Pool) -> list[dict]:
    migrations = _discover()
    async with pool.acquire() as conn:
        await ensure_table(conn)
        applied_versions = await applied(conn)

    result = []
    for m in migrations:
        result.append({
            "version": m.version,
            "name": m.name,
            "applied": m.version in applied_versions,
        })
    return result


def _discover() -> list[Migration]:
    migrations_dir = Path(MIGRATIONS_DIR)
    if not migrations_dir.is_dir():
        logger.warning("Migrations directory does not exist: %s", migrations_dir)
        return []

    result = []
    for fpath in sorted(migrations_dir.glob("*.sql")):
        match = _MIGRATION_PATTERN.match(fpath.name)
        if not match:
            logger.warning("Skipping file with invalid name: %s", fpath.name)
            continue

        version = int(match.group(1))
        name = match.group(2).replace("_", " ")

        content = fpath.read_text(encoding="utf-8")
        up_sql, _, down_sql = content.partition(_SEPARATOR)
        up_sql = up_sql.strip()
        down_sql = down_sql.strip() if down_sql else ""

        result.append(Migration(version=version, name=name, up_sql=up_sql, down_sql=down_sql))

    return result


def create_migration(description: str) -> str:
    migrations_dir = Path(MIGRATIONS_DIR)
    migrations_dir.mkdir(parents=True, exist_ok=True)

    existing = list(migrations_dir.glob("*.sql"))
    next_num = len(existing) + 1
    filename = f"{next_num:03d}_{description.lower().replace(' ', '_')}.sql"
    filepath = migrations_dir / filename

    template = f"""-- migrate:up
-- TODO: write your migration SQL here


-- migrate:down
-- TODO: write your rollback SQL here
"""
    filepath.write_text(template.lstrip(), encoding="utf-8")
    logger.info("Created migration: %s", filepath)
    return str(filepath)
