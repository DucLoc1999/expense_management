from dataclasses import dataclass
from db.database import get_db


@dataclass
class Category:
    id: int
    name: str
    is_default: bool


@dataclass
class Order:
    id: int
    name: str
    quantity: int
    price: int
    money: int
    shop: str
    category_id: int
    date: str
    notes: str
    sheet_synced: bool
    category_name: str = ""


async def get_categories() -> list[Category]:
    async with await get_db() as db:
        async with db.execute(
            "SELECT id, name, is_default FROM categories ORDER BY is_default DESC, name"
        ) as cur:
            rows = await cur.fetchall()
    return [Category(id=r["id"], name=r["name"], is_default=bool(r["is_default"])) for r in rows]


async def add_category(name: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    name = name.strip()
    if not name:
        return False, "Category name cannot be empty."
    async with await get_db() as db:
        try:
            await db.execute(
                "INSERT INTO categories (name, is_default) VALUES (?, 0)", (name,)
            )
            await db.commit()
            return True, f"Category '{name}' added."
        except Exception:
            return False, f"Category '{name}' already exists."


async def delete_category(name: str) -> tuple[bool, str]:
    """Returns (success, message). Cannot delete default categories."""
    name = name.strip()
    async with await get_db() as db:
        async with db.execute(
            "SELECT id, is_default FROM categories WHERE name = ?", (name,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False, f"Category '{name}' not found."
        if row["is_default"]:
            return False, f"Cannot delete default category '{name}'."
        await db.execute("DELETE FROM categories WHERE id = ?", (row["id"],))
        await db.commit()
    return True, f"Category '{name}' deleted."


async def save_order(
    name: str,
    quantity: int,
    price: int,
    money: int,
    shop: str,
    category_id: int,
    date: str,
    notes: str = "",
) -> int:
    """Insert order and return its id."""
    async with await get_db() as db:
        cur = await db.execute(
            """INSERT INTO orders (name, quantity, price, money, shop, category_id, date, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, quantity, price, money, shop, category_id, date, notes),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore[return-value]


async def get_unsynced_orders() -> list[Order]:
    async with await get_db() as db:
        async with db.execute(
            """SELECT o.*, c.name as category_name
               FROM orders o
               JOIN categories c ON o.category_id = c.id
               WHERE o.sheet_synced = 0
               ORDER BY o.created_at""",
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_order(r) for r in rows]


async def mark_synced(order_ids: list[int]) -> None:
    if not order_ids:
        return
    placeholders = ",".join("?" * len(order_ids))
    async with await get_db() as db:
        await db.execute(
            f"UPDATE orders SET sheet_synced = 1 WHERE id IN ({placeholders})",
            order_ids,
        )
        await db.commit()


async def get_recent_orders(limit: int = 10) -> list[Order]:
    async with await get_db() as db:
        async with db.execute(
            """SELECT o.*, c.name as category_name
               FROM orders o
               JOIN categories c ON o.category_id = c.id
               ORDER BY o.created_at DESC
               LIMIT ?""",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_order(r) for r in rows]


async def get_category_by_name(name: str) -> Category | None:
    async with await get_db() as db:
        async with db.execute(
            "SELECT id, name, is_default FROM categories WHERE name = ?", (name,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return Category(id=row["id"], name=row["name"], is_default=bool(row["is_default"]))


def _row_to_order(r) -> Order:
    return Order(
        id=r["id"],
        name=r["name"],
        quantity=r["quantity"],
        price=r["price"],
        money=r["money"],
        shop=r["shop"],
        category_id=r["category_id"],
        date=r["date"],
        notes=r["notes"] or "",
        sheet_synced=bool(r["sheet_synced"]),
        category_name=r["category_name"] if "category_name" in r.keys() else "",
    )
