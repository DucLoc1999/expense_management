from telegram import Update
from telegram.ext import ContextTypes

from bot.decorators import require_auth
from bot.models import _PENDING, _EDITING_IDX
from bot.responses import (
    session_expired,
    session_expired_short,
    already_processed,
    saved_line,
    saved_count_line,
    synced_suffix,
    saved_local_suffix,
    skipped,
    nothing_to_confirm,
    which_field,
    choose_category,
    fmt_order,
)
from bot.keyboards import (
    order_review_keyboard,
    edit_field_keyboard,
    category_select_keyboard,
)
from bot.states import State
from db.models import get_categories
from services.order_service import confirm_order, confirm_all_orders


@require_auth
async def cb_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text(session_expired())
        return State.IDLE

    po = pending[idx]
    if po.status != "pending":
        await query.edit_message_text(
            fmt_order(po, idx, len(pending)) + "\n\n" + already_processed(),
            parse_mode="Markdown",
        )
        return State.IDLE

    tele_user_id = update.effective_user.id
    ok, _ = await confirm_order(po, tele_user_id)

    suffix = synced_suffix() if ok else saved_local_suffix()
    await query.edit_message_text(
        fmt_order(po, idx, len(pending)) + "\n\n" + saved_line(suffix),
        parse_mode="Markdown",
    )
    return State.IDLE


@require_auth
async def cb_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text(session_expired_short())
        return State.IDLE

    pending[idx].status = "skipped"
    po = pending[idx]
    await query.edit_message_text(
        fmt_order(po, idx, len(pending)) + "\n\n" + skipped(),
        parse_mode="Markdown",
    )
    return State.IDLE


@require_auth
async def cb_confirm_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pending = context.user_data.get(_PENDING, [])
    to_confirm = [po for po in pending if po.status == "pending"]

    if not to_confirm:
        await query.edit_message_text(nothing_to_confirm())
        return State.IDLE

    tele_user_id = update.effective_user.id
    ok, n = await confirm_all_orders(pending, tele_user_id)

    suffix = synced_suffix() if ok else saved_local_suffix()
    await query.edit_message_text(saved_count_line(n, suffix))
    return State.IDLE


@require_auth
async def cb_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text(session_expired_short())
        return State.IDLE

    context.user_data[_EDITING_IDX] = idx
    po = pending[idx]
    await query.edit_message_text(
        fmt_order(po, idx, len(pending)) + "\n\n" + which_field(),
        parse_mode="Markdown",
        reply_markup=edit_field_keyboard(idx),
    )
    return State.IDLE


@require_auth
async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text(session_expired_short())
        return State.IDLE

    po = pending[idx]
    await query.edit_message_text(
        fmt_order(po, idx, len(pending)),
        parse_mode="Markdown",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE


@require_auth
async def cb_editfield(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    idx, field_name = int(parts[1]), parts[2]
    pending = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text(session_expired_short())
        return State.IDLE

    if field_name == "category":
        cats = await get_categories()
        cat_names = [c.name for c in cats]
        await query.edit_message_text(
            choose_category(),
            reply_markup=category_select_keyboard(idx, cat_names),
        )
        return State.IDLE

    context.user_data[_EDITING_IDX] = idx
    from bot.models import _EDITING_FIELD
    context.user_data[_EDITING_FIELD] = field_name
    from bot.responses import enter_field
    await query.edit_message_text(enter_field(field_name))
    return State.EDITING_FIELD_INPUT


@require_auth
async def cb_setcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 2)
    idx, cat_name = int(parts[1]), parts[2]
    pending = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text(session_expired_short())
        return State.IDLE

    pending[idx].category_name = cat_name
    po = pending[idx]
    await query.edit_message_text(
        fmt_order(po, idx, len(pending)),
        parse_mode="Markdown",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE
