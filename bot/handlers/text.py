from telegram import Update
from telegram.ext import ContextTypes

from bot.decorators import require_auth
from bot.models import _PENDING, _EDITING_IDX, _EDITING_FIELD
from bot.responses import (
    edit_nothing,
    edit_invalid,
    fmt_order,
)
from bot.keyboards import order_review_keyboard
from bot.states import State
from db.models import add_category


@require_auth
async def handle_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    idx = context.user_data.get(_EDITING_IDX)
    field_name = context.user_data.get(_EDITING_FIELD)
    pending = context.user_data.get(_PENDING, [])

    if idx is None or field_name is None or idx >= len(pending):
        await update.message.reply_text(edit_nothing())
        return State.IDLE

    text = update.message.text.strip()
    po = pending[idx]
    e = po.extracted

    try:
        if field_name == "name":
            e.name = text
        elif field_name == "money":
            e.money = int(text.replace(",", "").replace(".", ""))
        elif field_name == "shop":
            e.shop = text
        elif field_name == "notes":
            po.notes = text
    except ValueError:
        await update.message.reply_text(edit_invalid())
        return State.EDITING_FIELD_INPUT

    context.user_data.pop(_EDITING_FIELD, None)
    context.user_data.pop(_EDITING_IDX, None)

    await update.message.reply_text(
        fmt_order(po, idx, len(pending)),
        parse_mode="Markdown",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE


@require_auth
async def handle_addcat_input(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    _, msg = await add_category(name)
    await update.message.reply_text(msg)
    return State.IDLE
