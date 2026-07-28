import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import is_admin
from bot.decorators import require_auth
from bot.models import _PENDING, _EDITING_IDX, _EDITING_FIELD
from bot.responses import (
    edit_nothing,
    edit_invalid,
    fmt_order,
    categories_list,
)
from bot.keyboards import order_review_keyboard, category_menu_keyboard
from bot.states import State
from db.models import add_category, get_categories

logger = logging.getLogger(__name__)


def _clean_category_name(text: str) -> str:
    cleaned = re.sub(r'[^\w&,\-\s]', '', text, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', cleaned).strip()


@require_auth
async def handle_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = context.user_data.get("state")
    if state == State.EDITING_CATEGORIES:
        return await _handle_cat_edit_input(update, context)
    if state == State.ADDING_CATEGORY:
        return await _handle_cat_add_input(update, context)

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


async def _handle_cat_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Category list cannot be empty.")
        return State.IDLE
    names = [_clean_category_name(line) for line in text.split("\n") if line.strip()]
    names = [n for n in names if n]
    if not names:
        await update.message.reply_text("Category list cannot be empty.")
        return State.IDLE
    from db.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM categories WHERE is_default = FALSE")
        for name in names:
            await conn.execute(
                "INSERT INTO categories (name, is_default) VALUES ($1, FALSE) ON CONFLICT (name) DO NOTHING",
                name,
            )
    context.user_data.pop("state", None)
    cats = await get_categories()
    await update.message.reply_text(
        categories_list(cats),
        parse_mode="Markdown",
        reply_markup=category_menu_keyboard(is_admin(update.effective_user.id)),
    )
    return State.IDLE


async def _handle_cat_add_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = _clean_category_name(update.message.text.strip())
    if not name:
        await update.message.reply_text("Category name cannot be empty.")
        return State.ADDING_CATEGORY
    _, msg = await add_category(name)
    context.user_data.pop("state", None)
    cats = await get_categories()
    await update.message.reply_text(
        categories_list(cats),
        parse_mode="Markdown",
        reply_markup=category_menu_keyboard(is_admin(update.effective_user.id)),
    )
    return State.IDLE
