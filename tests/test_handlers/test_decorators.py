import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.decorators import require_auth
from bot.states import State


@require_auth
async def dummy_handler(_update, _context):  # pyright: ignore[reportUnusedParameter]
    return 42


@pytest.fixture
def make_update():
    def _make(user_id, is_callback=False):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = user_id
        if is_callback:
            update.callback_query = AsyncMock()
            update.callback_query.answer = AsyncMock()
        else:
            update.callback_query = None
        return update
    return _make


@pytest.mark.asyncio
class TestRequireAuth:
    async def test_authorized_user_passes_through(self, make_update):
        update = make_update(123456)
        context = MagicMock()

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await dummy_handler(update, context)

        assert result == 42

    async def test_unauthorized_user_returns_idle(self, make_update):
        update = make_update(999999)
        context = MagicMock()

        with patch("bot.decorators.is_authorized", return_value=False):
            result = await dummy_handler(update, context)

        assert result == State.IDLE

    async def test_unauthorized_callback_answers_query(self, make_update):
        update = make_update(999999, is_callback=True)
        context = MagicMock()

        with patch("bot.decorators.is_authorized", return_value=False):
            result = await dummy_handler(update, context)

        assert result == State.IDLE
        update.callback_query.answer.assert_awaited_once()

    async def test_no_effective_user_returns_idle(self):
        update = MagicMock()
        update.effective_user = None
        update.callback_query = None
        context = MagicMock()

        with patch("bot.decorators.is_authorized", return_value=False):
            result = await dummy_handler(update, context)

        assert result == State.IDLE

    async def test_preserves_function_name(self):
        assert dummy_handler.__name__ == "dummy_handler"
