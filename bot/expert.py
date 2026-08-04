import functools

from telegram import Update
from telegram.ext import ContextTypes

from bot.models import (
    _EXPERT_MODE,
    _EXPERT_BUSY,
    _EXPERT_SESSION,
    _EXPERT_CONTEXT,
    _EXPERT_FILTER,
)
from bot.responses import (
    expert_goodbye,
    expert_processing,
    expert_busy,
    expert_summary,
    expert_no_data,
)
from bot.keyboards import expert_screen_keyboard, expert_advisor_keyboard
from bot.states import State
from db.models import (
    close_expert_session,
    get_expert_messages,
    append_expert_message,
)
from services.expert import (
    build_summary,
    build_chart_url,
    resolve_preset,
    DEFAULT_PRESET,
    build_memory,
)
from services.gemini import ask_advisor


def is_expert_busy(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.get(_EXPERT_BUSY))


def expert_guard(func):
    """Shared busy-lock + mode-lock guard for command/callback handlers.

    While an AI response is in flight every action is ignored (except /start,
    which bypasses this guard). When advisor mode is active, the session is
    closed with a goodbye before the original handler executes.
    """

    @functools.wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if is_expert_busy(context):
            if update.callback_query:
                try:
                    await update.callback_query.answer()
                except Exception:
                    pass
            return State.IDLE
        await handle_expert_exit(update, context)
        return await func(update, context)

    return wrapper


async def handle_expert_exit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """If advisor mode is active, end the session gracefully. Returns True if it did."""
    if not context.user_data.get(_EXPERT_MODE):
        return False
    tele_user_id = update.effective_user.id
    session_id = context.user_data.get(_EXPERT_SESSION)
    if session_id:
        await close_expert_session(session_id, tele_user_id)
    message = update.effective_message
    if message is None and update.callback_query is not None:
        message = update.callback_query.message
    if message is not None:
        try:
            await message.reply_text(expert_goodbye())
        except Exception:
            pass
    context.user_data.pop(_EXPERT_MODE, None)
    context.user_data.pop(_EXPERT_BUSY, None)
    context.user_data.pop(_EXPERT_SESSION, None)
    context.user_data.pop(_EXPERT_CONTEXT, None)
    context.user_data["state"] = State.IDLE
    return True


async def ask_expert_question(
    update: Update, context: ContextTypes.DEFAULT_TYPE, question: str
) -> int:
    context.user_data[_EXPERT_BUSY] = True
    processing_msg = await update.effective_message.reply_text(expert_processing())

    tele_user_id = update.effective_user.id
    session_id = context.user_data.get(_EXPERT_SESSION)
    context_text = context.user_data.get(_EXPERT_CONTEXT) or ""
    memory: list[str] = []

    if session_id:
        rows = await get_expert_messages(session_id, tele_user_id, limit=20)
        memory = build_memory(list(reversed(rows)), question)
        await append_expert_message(session_id, "user", question)

    answer, error = await ask_advisor(context_text, memory, question)
    context.user_data.pop(_EXPERT_BUSY, None)

    text = answer or error or expert_busy()
    try:
        await processing_msg.edit_text(text, reply_markup=expert_advisor_keyboard())
    except Exception:
        pass

    if session_id and answer:
        await append_expert_message(session_id, "assistant", answer)
    return State.EXPERT_ADVICE


async def render_expert_summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit_message=None,
) -> int:
    """Render the expert screen (summary + chart) for the stored filter window."""
    tele_user_id = update.effective_user.id
    start, end = context.user_data.get(_EXPERT_FILTER) or resolve_preset(DEFAULT_PRESET)
    summary = await build_summary(tele_user_id, start, end)
    markup = expert_screen_keyboard()

    if summary is None:
        text = expert_no_data()
        if edit_message is not None:
            await edit_message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        else:
            await update.effective_message.reply_text(
                text, parse_mode="HTML", reply_markup=markup
            )
        return State.IDLE

    text = expert_summary(summary)
    chart_url = build_chart_url(summary)
    if edit_message is not None:
        await edit_message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.effective_message.reply_text(
            text, parse_mode="HTML", reply_markup=markup
        )
    if chart_url:
        try:
            await update.effective_chat.send_photo(photo=chart_url)
        except Exception:
            pass
    return State.IDLE
