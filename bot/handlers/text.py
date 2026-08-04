import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import is_admin, reload_users
from bot.decorators import require_auth
from bot.models import _PENDING, _EDITING_IDX, _EDITING_FIELD, _EXPERT_BUSY, _EXPERT_FILTER
from bot.responses import (
    edit_nothing,
    edit_invalid,
    fmt_order,
    categories_list,
    admin_adduser_ok,
    admin_adduser_invalid,
    admin_adduser_done,
    admin_removeuser_done,
    admin_removeuser_not_found,
    admin_users_list,
)
from bot.keyboards import order_review_keyboard, category_menu_keyboard, user_menu_keyboard
from bot.states import State
from bot.expert import handle_expert_exit, ask_expert_question, render_expert_summary
from db.models import (
    add_tele_user,
    remove_tele_user,
    get_all_tele_users,
    add_category,
    get_categories,
    replace_custom_categories,
)
from bot.i18n import _
from services.expert import parse_custom_range, RangeError

logger = logging.getLogger(__name__)


def _clean_category_name(text: str) -> str:
    cleaned = re.sub(r'[^\w&,\-\s]', '', text, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', cleaned).strip()


@require_auth
async def handle_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = context.user_data.get("state")
    if state == State.EXPERT_FILTER_FROM_TO:
        return await _handle_expert_range_input(update, context)
    if state == State.EXPERT_ADVICE:
        return await _handle_expert_question_input(update, context)
    if context.user_data.get(_EXPERT_BUSY):
        return State.IDLE
    await handle_expert_exit(update, context)
    if state == State.EDITING_CATEGORIES:
        return await _handle_cat_edit_input(update, context)
    if state == State.ADDING_CATEGORY:
        return await _handle_cat_add_input(update, context)
    if state == State.ADDING_USER:
        return await _handle_user_add_input(update, context)
    if state == State.REMOVING_USER:
        return await _handle_user_remove_input(update, context)

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
        parse_mode="HTML",
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
    await replace_custom_categories(names, update.effective_user.id)
    context.user_data.pop("state", None)
    cats = await get_categories(update.effective_user.id)
    await update.message.reply_text(
        categories_list(cats),
        parse_mode="HTML",
        reply_markup=category_menu_keyboard(is_admin(update.effective_user.id)),
    )
    return State.IDLE


async def _handle_cat_add_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = _clean_category_name(update.message.text.strip())
    if not name:
        await update.message.reply_text("Category name cannot be empty.")
        return State.ADDING_CATEGORY
    _, msg = await add_category(name, update.effective_user.id)
    context.user_data.pop("state", None)
    cats = await get_categories(update.effective_user.id)
    await update.message.reply_text(
        categories_list(cats),
        parse_mode="HTML",
        reply_markup=category_menu_keyboard(is_admin(update.effective_user.id)),
    )
    return State.IDLE


async def _handle_user_add_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    parts = text.split(None, 1)
    try:
        tele_user_id = int(parts[0])
    except (ValueError, IndexError):
        await update.message.reply_text(admin_adduser_invalid())
        return State.ADDING_USER
    name = parts[1] if len(parts) > 1 else ""
    await add_tele_user(tele_user_id, name)
    await reload_users()
    context.user_data.pop("state", None)
    users = await get_all_tele_users()
    await update.message.reply_text(
        admin_adduser_done(tele_user_id),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        admin_users_list(users),
        parse_mode="HTML",
        reply_markup=user_menu_keyboard(is_admin(update.effective_user.id)),
    )
    return State.IDLE


async def _handle_user_remove_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        tele_user_id = int(text)
    except ValueError:
        await update.message.reply_text("Invalid ID. Please enter a numeric user ID.")
        return State.REMOVING_USER
    ok = await remove_tele_user(tele_user_id)
    if ok:
        await reload_users()
        context.user_data.pop("state", None)
        await update.message.reply_text(
            admin_removeuser_done(tele_user_id),
            parse_mode="HTML",
        )
    else:
        context.user_data.pop("state", None)
        await update.message.reply_text(
            admin_removeuser_not_found(tele_user_id),
            parse_mode="HTML",
        )
    users = await get_all_tele_users()
    await update.message.reply_text(
        admin_users_list(users),
        parse_mode="HTML",
        reply_markup=user_menu_keyboard(is_admin(update.effective_user.id)),
    )
    return State.IDLE


async def _handle_expert_range_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    try:
        start, end = parse_custom_range(text)
    except RangeError as exc:
        await update.message.reply_text(_(f"expert.filter.error.{exc.message_key}"))
        return State.EXPERT_FILTER_FROM_TO
    context.user_data[_EXPERT_FILTER] = (start, end)
    context.user_data["state"] = State.IDLE
    await render_expert_summary(update, context)
    return State.IDLE


async def _handle_expert_question_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if context.user_data.get(_EXPERT_BUSY):
        return State.EXPERT_ADVICE
    question = update.message.text.strip()
    if not question:
        return State.EXPERT_ADVICE
    return await ask_expert_question(update, context, question)
