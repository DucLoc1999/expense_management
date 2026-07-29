from dataclasses import dataclass
from datetime import datetime

from db.database import get_pool


@dataclass
class Category:
    id: int
    name: str
    is_default: bool


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


async def get_categories() -> list[Category]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, is_default FROM categories ORDER BY is_default DESC, id"
        )
    return [
        Category(id=r["id"], name=r["name"], is_default=bool(r["is_default"]))
        for r in rows
    ]


async def add_category(name: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    name = name.strip()
    if not name:
        return False, "Category name cannot be empty."
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO categories (name, is_default) VALUES ($1, FALSE)", name
            )
            return True, f"Category '{name}' added."
        except Exception:
            return False, f"Category '{name}' already exists."


async def delete_category(name: str) -> tuple[bool, str]:
    """Returns (success, message). Cannot delete default categories."""
    name = name.strip()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, is_default FROM categories WHERE name = $1", name
        )
        if not row:
            return False, f"Category '{name}' not found."
        if row["is_default"]:
            return False, f"Cannot delete default category '{name}'."
        await conn.execute("DELETE FROM categories WHERE id = $1", row["id"])
    return True, f"Category '{name}' deleted."


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


async def get_category_by_name(name: str) -> Category | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, is_default FROM categories WHERE name = $1", name
        )
    if not row:
        return None
    return Category(id=row["id"], name=row["name"], is_default=bool(row["is_default"]))


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
