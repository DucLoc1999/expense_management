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
    slug: str | None = None


@dataclass
class Order:
    id: int
    name: str
    money: int
    shop: str
    category_id: int
    date: str
    notes: str
    sheet_synced: bool
    payment_source: str = "shopee"
    category_name: str = ""


def _row_to_category(r) -> Category:
    return Category(
        id=r["id"],
        name=r["name"],
        is_system=bool(r["is_system"]),
        user_id=r["user_id"],
        parent_id=r["parent_id"],
        slug=r["slug"],
    )


async def get_categories(tele_user_id: int) -> list[Category]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, is_system, user_id, parent_id, slug FROM categories
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
               WHERE name = $1 AND (user_id IS NULL OR user_id = $2)
               LIMIT 1""",
            name,
            tele_user_id,
        )
        if existing:
            return False, f"Category '{name}' already exists."
        await conn.execute(
            "INSERT INTO categories (name, is_system, user_id) VALUES ($1, FALSE, $2)",
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
                    "SELECT 1 FROM categories WHERE user_id IS NULL AND name = $1",
                    name,
                )
                if not exists:
                    await conn.execute(
                        "INSERT INTO categories (name, is_system, user_id) VALUES ($1, FALSE, $2)",
                        name,
                        tele_user_id,
                    )


async def save_order(
    name: str,
    money: int,
    shop: str,
    category_id: int,
    date: str,
    notes: str = "",
    payment_source: str = "shopee",
    tele_user_id: int = 0,
) -> int:
    """Insert order and return its id."""
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d").date()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO orders (name, money, shop, category_id, date, notes, payment_source, tele_user_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
            name,
            money,
            shop,
            category_id,
            date,
            notes,
            payment_source,
            tele_user_id,
        )
        return row["id"]


async def get_unsynced_orders(tele_user_id: int) -> list[Order]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT o.*, c.name as category_name
               FROM orders o
               JOIN categories c ON o.category_id = c.id
               WHERE o.sheet_synced = FALSE AND o.tele_user_id = $1
               ORDER BY o.created_at""",
            tele_user_id,
        )
    return [_row_to_order(r) for r in rows]


async def mark_synced(order_ids: list[int]) -> None:
    if not order_ids:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE orders SET sheet_synced = TRUE WHERE id = ANY($1)",
            order_ids,
        )


async def get_recent_orders(tele_user_id: int, limit: int = 10) -> list[Order]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT o.*, c.name as category_name
               FROM orders o
               JOIN categories c ON o.category_id = c.id
               WHERE o.tele_user_id = $1
               ORDER BY o.created_at DESC
               LIMIT $2""",
            tele_user_id,
            limit,
        )
    return [_row_to_order(r) for r in rows]


async def get_sheet_id(tele_user_id: int) -> int | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT sheet_id FROM telegram_users WHERE tele_user_id = $1",
            tele_user_id,
        )
    return row["sheet_id"] if row else None


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
            "SELECT tele_user_id, name, role, sheet_id FROM telegram_users ORDER BY tele_user_id"
        )
    return [dict(r) for r in rows]


async def set_sheet_id(tele_user_id: int, sheet_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO telegram_users (tele_user_id, sheet_id) VALUES ($1, $2) "
            "ON CONFLICT (tele_user_id) DO UPDATE SET sheet_id = $2",
            tele_user_id,
            sheet_id,
        )


async def get_category_by_name(name: str, tele_user_id: int) -> Category | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, name, is_system, user_id, parent_id, slug FROM categories
               WHERE name = $1 AND (user_id IS NULL OR user_id = $2)
               ORDER BY COALESCE(user_id = $2, FALSE) DESC, id
               LIMIT 1""",
            name,
            tele_user_id,
        )
    if not row:
        return None
    return _row_to_category(row)


def _row_to_order(r) -> Order:
    return Order(
        id=r["id"],
        name=r["name"],
        money=r["money"],
        shop=r["shop"],
        category_id=r["category_id"],
        date=str(r["date"]),
        notes=r["notes"] or "",
        sheet_synced=bool(r["sheet_synced"]),
        payment_source=r.get("payment_source", "shopee") or "shopee",
        category_name=r.get("category_name", "") or "",
    )
