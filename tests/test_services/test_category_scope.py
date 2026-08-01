import pytest
from unittest.mock import AsyncMock, patch

from db.models import (
    add_category,
    delete_category,
    get_categories,
    get_category_by_name,
    replace_custom_categories,
)


def _row(cid, name, is_system, user_id=None, parent_id=None, name_vi=None):
    return {
        "id": cid,
        "name": name,
        "is_system": is_system,
        "user_id": user_id,
        "parent_id": parent_id,
        "name_vi": name_vi,
    }


class _FakeTx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class _FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return _FakeAcquire(self.conn)


class _FakeConn:
    def __init__(self):
        self.fetch = AsyncMock(return_value=[])
        self.fetchrow = AsyncMock(return_value=None)
        self.fetchval = AsyncMock(return_value=None)
        self.execute = AsyncMock(return_value="OK")

    def transaction(self):
        return _FakeTx(self)


@pytest.fixture
def db():
    conn = _FakeConn()
    pool = _FakePool(conn)
    with patch("db.models.get_pool", new_callable=AsyncMock, return_value=pool):
        yield conn


@pytest.mark.asyncio
class TestGetCategories:
    async def test_returns_system_and_own_custom(self, db):
        db.fetch.return_value = [
            _row(1, "Food & Drink", True, None, None, "Ăn uống"),
            _row(2, "Gia vị", False, 111),
        ]

        cats = await get_categories(111)

        assert [c.name for c in cats] == ["Food & Drink", "Gia vị"]
        assert cats[0].name_vi == "Ăn uống"
        assert cats[0].is_system is True
        assert cats[0].user_id is None
        assert cats[1].is_system is False
        assert cats[1].user_id == 111
        assert db.fetch.await_args.args[1] == 111


@pytest.mark.asyncio
class TestGetCategoryByName:
    async def test_prefers_user_custom_over_system(self, db):
        db.fetchrow.return_value = _row(5, "Gia vị", False, 111)

        cat = await get_category_by_name("Gia vị", 111)

        assert cat is not None
        assert cat.is_system is False
        assert cat.user_id == 111
        args = db.fetchrow.await_args.args
        assert args[1] == "Gia vị"
        assert args[2] == 111

    async def test_matches_by_vietnamese_name(self, db):
        db.fetchrow.return_value = _row(1, "Food & Drink", True, None, None, "Ăn uống")

        cat = await get_category_by_name("Ăn uống", 222)

        assert cat is not None
        assert cat.name == "Food & Drink"
        assert cat.name_vi == "Ăn uống"
        assert cat.is_system is True
        assert cat.user_id is None

    async def test_returns_system_when_no_custom(self, db):
        db.fetchrow.return_value = _row(1, "Food & Drink", True, None, None, "Ăn uống")

        cat = await get_category_by_name("Food & Drink", 222)

        assert cat is not None
        assert cat.is_system is True
        assert cat.user_id is None

    async def test_returns_none_when_missing(self, db):
        db.fetchrow.return_value = None

        assert await get_category_by_name("Không có", 111) is None


@pytest.mark.asyncio
class TestAddCategory:
    async def test_rejects_existing_system_or_own_name(self, db):
        db.fetchval.return_value = 1

        ok, msg = await add_category("Ăn uống", 111)

        assert ok is False
        assert "already exists" in msg
        db.execute.assert_not_awaited()

    async def test_inserts_scoped_custom_category(self, db):
        db.fetchval.return_value = None

        ok, _ = await add_category("Gia vị", 111)

        assert ok is True
        db.execute.assert_awaited_once()
        args = db.execute.await_args.args
        assert "INSERT INTO categories" in args[0]
        assert args[1] == "Gia vị"
        assert args[2] == "Gia vị"
        assert args[3] == 111


@pytest.mark.asyncio
class TestDeleteCategory:
    async def test_rejects_system_category(self, db):
        db.fetchrow.return_value = _row(1, "Ăn uống", True, None)

        ok, msg = await delete_category("Ăn uống", 111)

        assert ok is False
        assert "system" in msg
        db.execute.assert_not_awaited()

    async def test_rejects_other_users_category(self, db):
        db.fetchrow.return_value = _row(3, "Gia vị", False, 222)

        ok, msg = await delete_category("Gia vị", 111)

        assert ok is False
        assert "another user" in msg
        db.execute.assert_not_awaited()

    async def test_deletes_own_custom_category(self, db):
        db.fetchrow.return_value = _row(3, "Gia vị", False, 111)

        ok, _ = await delete_category("Gia vị", 111)

        assert ok is True
        db.execute.assert_awaited_once()


@pytest.mark.asyncio
class TestReplaceCustomCategories:
    async def test_deletes_only_own_custom_and_inserts_scoped(self, db):
        await replace_custom_categories(["A", "B"], 111)

        calls = db.execute.await_args_list
        assert len(calls) == 3
        delete_args = calls[0].args
        assert "DELETE FROM categories WHERE user_id = $1 AND is_system = FALSE" in delete_args[0]
        assert delete_args[1] == 111
        for call in calls[1:]:
            assert "INSERT INTO categories" in call.args[0]
            assert call.args[2] == call.args[1]
            assert call.args[3] == 111

    async def test_skips_names_used_by_system_categories(self, db):
        db.fetchval.side_effect = [1, None]

        await replace_custom_categories(["Ăn uống", "Gia vị"], 111)

        insert_calls = [
            c for c in db.execute.await_args_list if "INSERT INTO" in c.args[0]
        ]
        assert len(insert_calls) == 1
        assert insert_calls[0].args[1] == "Gia vị"
