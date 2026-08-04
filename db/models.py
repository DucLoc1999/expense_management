from dataclasses import dataclass
from datetime import datetime

from db.database import get_pool


@dataclass
class Category:
    id: int
    name: str
    is_system: bool
    user_id: int | None = None
    parent_id: int | None = None
    name_vi: str | None = None


@dataclass
class Bill:
    id: int
    name: str
    money: int
    shop: str
    date: str
    notes: str
    payment_source: str = "shopee"
    category_name: str = ""
    category_name_vi: str = ""


@dataclass
class CategoryTotal:
    category_name: str
    name_vi: str | None
    total: int


@dataclass
class PeriodStats:
    count: int
    total: int
    avg_per_day: float
    avg_per_bill: float


def _row_to_category(r) -> Category:
    return Category(
        id=r["id"],
        name=r["name"],
        is_system=bool(r["is_system"]),
        user_id=r["user_id"],
        parent_id=r["parent_id"],
        name_vi=r["name_vi"],
    )


async def get_categories(tele_user_id: int) -> list[Category]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, name_vi, is_system, user_id, parent_id FROM categories
               WHERE user_id IS NULL OR user_id = $1
               ORDER BY is_system DESC, id""",
            tele_user_id,
        )
    return [_row_to_category(r) for r in rows]


async def add_category(name: str, tele_user_id: int) -> tuple[bool, str]:
    """Returns (success, message). Rejects names used by system or the user's own set."""
    name = name.strip()
    if not name:
        return False, "Category name cannot be empty."
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            """SELECT 1 FROM categories
               WHERE (name = $1 OR name_vi = $1)
                 AND (user_id IS NULL OR user_id = $2)
               LIMIT 1""",
            name,
            tele_user_id,
        )
        if existing:
            return False, f"Category '{name}' already exists."
        await conn.execute(
            "INSERT INTO categories (name, name_vi, is_system, user_id) VALUES ($1, $2, FALSE, $3)",
            name,
            name,
            tele_user_id,
        )
    return True, f"Category '{name}' added."


async def delete_category(name: str, tele_user_id: int) -> tuple[bool, str]:
    """Returns (success, message). Cannot delete system or other users' categories."""
    name = name.strip()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, is_system, user_id FROM categories
               WHERE name = $1 AND (user_id = $2 OR user_id IS NULL)
               ORDER BY COALESCE(user_id = $2, FALSE) DESC
               LIMIT 1""",
            name,
            tele_user_id,
        )
        if not row:
            return False, f"Category '{name}' not found."
        if row["is_system"]:
            return False, f"Cannot delete system category '{name}'."
        if row["user_id"] != tele_user_id:
            return False, f"Cannot delete another user's category '{name}'."
        await conn.execute("DELETE FROM categories WHERE id = $1", row["id"])
    return True, f"Category '{name}' deleted."


async def replace_custom_categories(names: list[str], tele_user_id: int) -> None:
    """Replace only the user's own custom categories. Skips names used by system categories."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM categories WHERE user_id = $1 AND is_system = FALSE",
                tele_user_id,
            )
            for name in names:
                exists = await conn.fetchval(
                    "SELECT 1 FROM categories WHERE user_id IS NULL AND (name = $1 OR name_vi = $1)",
                    name,
                )
                if not exists:
                    await conn.execute(
                        "INSERT INTO categories (name, name_vi, is_system, user_id) VALUES ($1, $2, FALSE, $3)",
                        name,
                        name,
                        tele_user_id,
                    )


async def save_bill(
    name: str,
    money: int,
    shop: str,
    category_id: int,
    date: str,
    notes: str = "",
    payment_source: str = "shopee",
    tele_user_id: int = 0,
) -> int:
    """Insert a bill and return the new bill id."""
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d").date()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO bills (name, money, shop, date, notes, payment_source, tele_user_id, category_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
            name,
            money,
            shop,
            date,
            notes,
            payment_source,
            tele_user_id,
            category_id,
        )
        return row["id"]


async def get_recent_bills(tele_user_id: int, limit: int = 10) -> list[Bill]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT b.*, c.name as category_name, c.name_vi as category_name_vi
               FROM bills b
               LEFT JOIN categories c ON b.category_id = c.id
               WHERE b.tele_user_id = $1
               ORDER BY b.created_at DESC
               LIMIT $2""",
            tele_user_id,
            limit,
        )
    return [_row_to_bill(r) for r in rows]


async def add_tele_user(tele_user_id: int, name: str = "", role: str = "") -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO telegram_users (tele_user_id, name, role) VALUES ($1, $2, $3) "
            "ON CONFLICT (tele_user_id) DO UPDATE SET name = $2, role = $3",
            tele_user_id, name, role,
        )


async def remove_tele_user(tele_user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM telegram_users WHERE tele_user_id = $1",
            tele_user_id,
        )
    return result != "DELETE 0"


async def get_first_admin_id() -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tele_user_id FROM telegram_users WHERE role = 'admin' ORDER BY id LIMIT 1"
        )
    return row["tele_user_id"] if row else None


async def get_all_tele_users() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT tele_user_id, name, role FROM telegram_users ORDER BY tele_user_id"
        )
    return [dict(r) for r in rows]


async def get_category_by_name(name: str, tele_user_id: int) -> Category | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, name, name_vi, is_system, user_id, parent_id FROM categories
               WHERE (name = $1 OR name_vi = $1)
                 AND (user_id IS NULL OR user_id = $2)
               ORDER BY COALESCE(user_id = $2, FALSE) DESC, id
               LIMIT 1""",
            name,
            tele_user_id,
        )
    if not row:
        return None
    return _row_to_category(row)


def _row_to_bill(r) -> Bill:
    return Bill(
        id=r["id"],
        name=r["name"],
        money=r["money"],
        shop=r["shop"],
        date=str(r["date"]),
        notes=r["notes"] or "",
        payment_source=r.get("payment_source", "shopee") or "shopee",
        category_name=r.get("category_name", "") or "",
        category_name_vi=r.get("category_name_vi", "") or "",
    )


def _as_date_str(v) -> str:
    if isinstance(v, str):
        return v
    return v.strftime("%Y-%m-%d")


def _days_in_range(start, end) -> int:
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d").date()
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d").date()
    return (end - start).days + 1


async def get_period_stats(tele_user_id: int, start, end) -> PeriodStats | None:
    """Aggregate stats for the window. Returns None when there are no bills."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT COUNT(*)::int AS count,
                      COALESCE(SUM(money), 0)::bigint AS total
               FROM bills
               WHERE tele_user_id = $1 AND date BETWEEN $2 AND $3""",
            tele_user_id,
            _as_date_str(start),
            _as_date_str(end),
        )
    count = row["count"]
    if not count:
        return None
    total = int(row["total"])
    days = max(_days_in_range(start, end), 1)
    return PeriodStats(
        count=count,
        total=total,
        avg_per_day=total / days,
        avg_per_bill=total / count,
    )


async def create_expert_session(tele_user_id: int, session_uuid: str, start, end) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO expert_sessions (tele_user_id, session_uuid, filter_start, filter_end)
               VALUES ($1, $2, $3, $4) RETURNING id""",
            tele_user_id,
            session_uuid,
            _as_date_str(start),
            _as_date_str(end),
        )
    return row["id"]


async def append_expert_message(session_id: int, role: str, content: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO expert_messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_id,
            role,
            content,
        )


async def get_expert_messages(session_id: int, tele_user_id: int, limit: int = 50) -> list[dict]:
    """Most recent messages of a session, scoped by owner, newest first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT m.id, m.role, m.content, m.created_at
               FROM expert_messages m
               JOIN expert_sessions s ON s.id = m.session_id
               WHERE m.session_id = $1 AND s.tele_user_id = $2
               ORDER BY m.id DESC
               LIMIT $3""",
            session_id,
            tele_user_id,
            limit,
        )
    return [dict(r) for r in rows]


async def close_expert_session(session_id: int, tele_user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE expert_sessions SET ended_at = NOW()
               WHERE id = $1 AND tele_user_id = $2 AND ended_at IS NULL""",
            session_id,
            tele_user_id,
        )


async def get_bills_in_range(
    tele_user_id: int, start, end, limit: int = 50
) -> list[Bill]:
    """Bills within [start, end] (inclusive) joined with categories, newest first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT b.*, c.name as category_name, c.name_vi as category_name_vi
               FROM bills b
               LEFT JOIN categories c ON b.category_id = c.id
               WHERE b.tele_user_id = $1
                 AND b.date >= $2 AND b.date <= $3
               ORDER BY b.date DESC, b.id DESC
               LIMIT $4""",
            tele_user_id,
            _as_date_str(start),
            _as_date_str(end),
            limit,
        )
    return [_row_to_bill(r) for r in rows]


async def get_category_totals(
    tele_user_id: int, start, end
) -> list[CategoryTotal]:
    """Per-category totals as CategoryTotal, ordered by total desc."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT c.name as category_name, c.name_vi, SUM(b.money)::bigint as total
               FROM bills b
               LEFT JOIN categories c ON b.category_id = c.id
               WHERE b.tele_user_id = $1
                 AND b.date >= $2 AND b.date <= $3
               GROUP BY c.id
               ORDER BY total DESC""",
            tele_user_id,
            _as_date_str(start),
            _as_date_str(end),
        )
    return [
        CategoryTotal(
            category_name=r["category_name"] or "",
            name_vi=r["name_vi"],
            total=int(r["total"] or 0),
        )
        for r in rows
    ]
