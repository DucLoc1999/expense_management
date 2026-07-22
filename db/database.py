import aiosqlite
from pathlib import Path
import config

DB_PATH = Path(config.DB_PATH)


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_default BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                price INTEGER NOT NULL,
                money INTEGER NOT NULL,
                shop TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                date DATE NOT NULL,
                notes TEXT DEFAULT '',
                sheet_synced BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );
        """)
        await db.commit()
        await _seed_categories(db)


_DEFAULT_CATEGORIES = [
    "Ăn uống",
    "Đồ gia dụng",
    "Điện tử",
    "Thời trang",
    "Sức khỏe & Làm đẹp",
    "Văn phòng phẩm",
    "Mẹ & Bé",
    "Thú cưng",
    "Thể thao",
    "Khác",
]


async def _seed_categories(db: aiosqlite.Connection) -> None:
    for name in _DEFAULT_CATEGORIES:
        await db.execute(
            "INSERT OR IGNORE INTO categories (name, is_default) VALUES (?, 1)",
            (name,),
        )
    await db.commit()
