import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers.commands import cmd_history
from bot.handlers.callbacks import cb_main_menu, cb_expert_end
from bot.handlers.image import handle_image
from bot.handlers.text import handle_field_input
from bot.expert import ask_expert_question, handle_expert_exit, expert_guard
from bot.states import State


def _make_update():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 111
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


def _make_context(user_data=None):
    context = MagicMock()
    context.user_data = user_data if user_data is not None else {}
    return context


@pytest.mark.asyncio
class TestHandleExpertExit:
    async def test_returns_false_when_not_in_mode(self):
        update = _make_update()
        context = _make_context()

        assert await handle_expert_exit(update, context) is False

    async def test_ends_session_and_clears_state(self):
        update = _make_update()
        context = _make_context(
            {"expert_mode": True, "expert_session": 5, "state": State.EXPERT_ADVICE}
        )
        with patch("bot.expert.close_expert_session", new_callable=AsyncMock) as close:
            result = await handle_expert_exit(update, context)

        assert result is True
        close.assert_awaited_once_with(5, 111)
        assert "expert_mode" not in context.user_data
        assert context.user_data["state"] == State.IDLE


@pytest.mark.asyncio
class TestFieldInputRouting:
    @patch("bot.handlers.text.render_expert_summary", new_callable=AsyncMock)
    async def test_routes_custom_range_input(self, mock_render):
        update = _make_update()
        update.message.text = "01/07/2026 - 31/07/2026"
        context = _make_context({"state": State.EXPERT_FILTER_FROM_TO})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await handle_field_input(update, context)

        assert result == State.IDLE
        assert context.user_data["expert_filter"] is not None
        mock_render.assert_awaited_once()

    @patch("bot.expert.ask_advisor", new_callable=AsyncMock)
    @patch("bot.expert.get_expert_messages", new_callable=AsyncMock)
    @patch("bot.expert.append_expert_message", new_callable=AsyncMock)
    async def test_routes_question_input(self, mock_append, mock_msgs, mock_advisor):
        update = _make_update()
        update.message.text = "Where did I spend most?"
        context = _make_context(
            {
                "state": State.EXPERT_ADVICE,
                "expert_mode": True,
                "expert_session": 7,
                "expert_context": "data...",
            }
        )
        mock_msgs.return_value = []
        mock_advisor.return_value = ("Answer", None)

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await handle_field_input(update, context)

        assert result == State.EXPERT_ADVICE
        mock_advisor.assert_awaited_once()

    async def test_busy_lock_ignores_input(self):
        update = _make_update()
        context = _make_context({"expert_busy": True})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await handle_field_input(update, context)

        assert result == State.IDLE


@pytest.mark.asyncio
class TestImageGuard:
    async def test_busy_blocks_image(self):
        update = _make_update()
        context = _make_context({"expert_busy": True})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await handle_image(update, context)

        assert result == State.EXPERT_ADVICE
        update.message.reply_text.assert_not_awaited()

    async def test_advisor_mode_rejects_image(self):
        update = _make_update()
        context = _make_context({"expert_mode": True})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await handle_image(update, context)

        assert result == State.EXPERT_ADVICE
        update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
class TestAskExpertQuestion:
    @patch("bot.expert.ask_advisor", new_callable=AsyncMock)
    @patch("bot.expert.get_expert_messages", new_callable=AsyncMock)
    @patch("bot.expert.append_expert_message", new_callable=AsyncMock)
    async def test_sets_and_clears_busy(self, mock_append, mock_msgs, mock_advisor):
        update = _make_update()
        context = _make_context(
            {"expert_session": 7, "expert_context": "ctx", "state": State.EXPERT_ADVICE}
        )
        mock_msgs.return_value = []
        mock_advisor.return_value = ("Advice", None)

        result = await ask_expert_question(update, context, "help me")

        assert result == State.EXPERT_ADVICE
        assert context.user_data.get("expert_busy") is None
        call_args = mock_advisor.await_args
        assert call_args.args[0] == "ctx"
        assert call_args.args[2] == "help me"
        assert any("help me" in line for line in call_args.args[1])

    @patch("bot.expert.ask_advisor", new_callable=AsyncMock)
    @patch("bot.expert.get_expert_messages", new_callable=AsyncMock)
    @patch("bot.expert.append_expert_message", new_callable=AsyncMock)
    async def test_persists_user_and_assistant_messages(self, mock_append, mock_msgs, mock_advisor):
        update = _make_update()
        context = _make_context(
            {"expert_session": 7, "expert_context": "ctx", "state": State.EXPERT_ADVICE}
        )
        mock_msgs.return_value = []
        mock_advisor.return_value = ("Advice", None)

        await ask_expert_question(update, context, "help me")

        assert mock_append.await_args_list[0].args == (7, "user", "help me")
        assert mock_append.await_args_list[1].args == (7, "assistant", "Advice")

    @patch("bot.expert.ask_advisor", new_callable=AsyncMock)
    @patch("bot.expert.get_expert_messages", new_callable=AsyncMock)
    @patch("bot.expert.append_expert_message", new_callable=AsyncMock)
    async def test_skips_assistant_persistence_on_error(self, mock_append, mock_msgs, mock_advisor):
        update = _make_update()
        context = _make_context({"expert_session": 7, "expert_context": "ctx"})
        mock_msgs.return_value = []
        mock_advisor.return_value = (None, "Gemini API error: 500")

        await ask_expert_question(update, context, "help me")

        assert mock_append.await_count == 1
        assert mock_append.await_args.args == (7, "user", "help me")


@pytest.mark.asyncio
class TestCommandBusyLock:
    async def test_ignores_command_while_busy(self):
        update = _make_update()
        context = _make_context({"expert_busy": True})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await cmd_history(update, context)

        assert result == State.IDLE
        update.message.reply_text.assert_not_awaited()

    async def test_executes_command_when_not_busy(self):
        update = _make_update()
        context = _make_context({})
        update.effective_user.id = 111

        with (
            patch("bot.decorators.is_authorized", return_value=True),
            patch("db.models.get_recent_bills", new_callable=AsyncMock, return_value=[]),
        ):
            result = await cmd_history(update, context)

        assert result == State.IDLE
        update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
class TestCallbackGuard:
    async def test_ignores_callback_while_busy(self):
        update = _make_update()
        context = _make_context({"expert_busy": True})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await cb_main_menu(update, context)

        assert result == State.IDLE
        update.callback_query.answer.assert_awaited_once()
        update.callback_query.edit_message_text.assert_not_awaited()

    async def test_expert_end_ignored_while_busy(self):
        update = _make_update()
        context = _make_context({"expert_busy": True, "expert_mode": True})

        with patch("bot.decorators.is_authorized", return_value=True):
            result = await cb_expert_end(update, context)

        assert result == State.EXPERT_ADVICE
        assert context.user_data.get("expert_mode") is True

    async def test_closes_session_before_executing(self):
        update = _make_update()
        context = _make_context(
            {"expert_mode": True, "expert_session": 5, "state": State.EXPERT_ADVICE}
        )
        update.effective_user.id = 111

        with (
            patch("bot.decorators.is_authorized", return_value=True),
            patch("bot.expert.close_expert_session", new_callable=AsyncMock) as close,
        ):
            result = await cb_main_menu(update, context)

        assert result == State.IDLE
        close.assert_awaited_once_with(5, 111)
        assert "expert_mode" not in context.user_data
        assert context.user_data["state"] == State.IDLE
        update.callback_query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
class TestExpertGuardHelper:
    async def test_guard_passthrough_when_not_busy(self):
        update = _make_update()
        context = _make_context({})

        async def handler(update, context):
            return State.IDLE

        result = await expert_guard(handler)(update, context)

        assert result == State.IDLE

    async def test_guard_ignores_when_busy(self):
        update = _make_update()
        context = _make_context({"expert_busy": True})

        async def handler(update, context):
            raise AssertionError("handler should not run while busy")

        result = await expert_guard(handler)(update, context)

        assert result == State.IDLE
