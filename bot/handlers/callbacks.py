from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import is_admin
from bot.decorators import require_auth
from bot.models import _PENDING, _EDITING_IDX
from bot.responses import (
    session_expired,
    session_expired_short,
    already_processed,
    saved_line,
    saved_count_line,
    skipped,
    nothing_to_confirm,
    which_field,
    choose_category,
    fmt_order,
    categories_list,
    category_edit_prompt,
    category_menu_title,
    category_add_prompt,
    category_remove_prompt,
    welcome,
    admin_denied,
    admin_users_list,
)
from bot.keyboards import (
    order_review_keyboard,
    edit_field_keyboard,
    category_select_keyboard,
    welcome_keyboard,
    category_menu_keyboard,
    category_remove_keyboard,
    language_keyboard,
    main_menu_only_keyboard,
    back_to_category_manager_keyboard,
    user_menu_keyboard,
)

from bot.states import State
from bot.i18n import localized_name
from db.models import get_categories, get_recent_bills, add_category, delete_category, get_all_tele_users
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
            parse_mode="HTML",
        )
        return State.IDLE

    tele_user_id = update.effective_user.id
    await confirm_order(po, tele_user_id)

    await query.edit_message_text(
        fmt_order(po, idx, len(pending)) + "\n\n" + saved_line(),
        parse_mode="HTML",
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
        parse_mode="HTML",
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
    n = await confirm_all_orders(pending, tele_user_id)

    await query.edit_message_text(saved_count_line(n))
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
        parse_mode="HTML",
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
        parse_mode="HTML",
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
        cats = await get_categories(update.effective_user.id)
        cat_names = [localized_name(c.name, c.name_vi) for c in cats]
        await query.edit_message_text(
            choose_category(),
            reply_markup=category_select_keyboard(idx, cat_names),
        )
        return State.IDLE

    context.user_data[_EDITING_IDX] = idx
    from bot.models import _EDITING_FIELD

    context.user_data[_EDITING_FIELD] = field_name
    from bot.responses import enter_field

    await query.edit_message_text(
        enter_field(field_name),
        reply_markup=category_menu_keyboard(True),
        # main_menu_only_keyboard(),
    )
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
        parse_mode="HTML",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE


@require_auth
async def cb_welcome_categories(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    cats = await get_categories(tele_user_id)
    await query.edit_message_text(
        categories_list(cats),
        parse_mode="HTML",
        reply_markup=category_menu_keyboard(is_admin(tele_user_id)),
    )
    return State.IDLE


@require_auth
async def cb_welcome_history(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    bills = await get_recent_bills(tele_user_id, limit=5)
    from bot.responses import history_list

    text = history_list(bills)
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_only_keyboard(),
    )
    return State.IDLE


@require_auth
async def cb_welcome_language(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    from bot.responses import language_invalid
    from bot.i18n import get_available_locales

    langs = ", ".join(get_available_locales())
    await query.edit_message_text(
        language_invalid(langs),
        reply_markup=language_keyboard(),
    )
    return State.IDLE


@require_auth
async def cb_welcome_users(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    cats = await get_categories(tele_user_id)
    await query.edit_message_text(
        categories_list(cats),
        parse_mode="HTML",
        reply_markup=category_menu_keyboard(is_admin(tele_user_id)),
    )
    return State.IDLE


@require_auth
async def cb_user_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("Access denied.")
        return State.IDLE
    from bot.responses import admin_adduser_prompt
    await query.edit_message_text(
        admin_adduser_prompt(),
        parse_mode="HTML",
    )
    context.user_data["state"] = State.ADDING_USER
    return State.ADDING_USER


@require_auth
async def cb_user_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("Access denied.")
        return State.IDLE
    from bot.responses import admin_removeuser_prompt
    await query.edit_message_text(
        admin_removeuser_prompt(),
        parse_mode="HTML",
    )
    context.user_data["state"] = State.REMOVING_USER
    return State.REMOVING_USER


@require_auth
async def cb_cat_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    if not is_admin(tele_user_id):
        await query.edit_message_text("Access denied.")
        return State.IDLE
    await query.edit_message_text(
        category_add_prompt(),
        reply_markup=back_to_category_manager_keyboard(),
    )
    context.user_data["state"] = State.ADDING_CATEGORY
    return State.ADDING_CATEGORY


@require_auth
async def cb_cat_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    if not is_admin(tele_user_id):
        await query.edit_message_text("Access denied.")
        return State.IDLE
    await query.edit_message_text(
        category_edit_prompt(),
        reply_markup=back_to_category_manager_keyboard(),
    )
    context.user_data["state"] = State.EDITING_CATEGORIES
    return State.EDITING_CATEGORIES


@require_auth
async def cb_cat_list(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    cats = await get_categories(update.effective_user.id)
    from bot.responses import categories_list

    await query.edit_message_text(
        categories_list(cats),
        parse_mode="HTML",
        reply_markup=back_to_category_manager_keyboard(),
    )
    return State.IDLE


@require_auth
async def cb_language_set(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    code = query.data.split(":", 1)[1]
    from bot.i18n import set_locale

    if set_locale(code):
        await query.edit_message_text(
            welcome(), parse_mode="HTML", reply_markup=welcome_keyboard()
        )
    else:
        await query.edit_message_text("Invalid language.")
    return State.IDLE


@require_auth
async def cb_cat_remove(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    if not is_admin(tele_user_id):
        await query.edit_message_text("Access denied.")
        return State.IDLE
    cats = await get_categories(tele_user_id)
    removable = [c for c in cats if not c.is_system]
    if not removable:
        from bot.responses import category_remove_empty

        await query.edit_message_text(category_remove_empty())
        return State.IDLE
    await query.edit_message_text(
        category_remove_prompt(),
        reply_markup=category_remove_keyboard(cats),
    )
    return State.IDLE


@require_auth
async def cb_cat_rm(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    if not is_admin(tele_user_id):
        await query.edit_message_text("Access denied.")
        return State.IDLE
    cat_name = query.data.split(":", 1)[1]
    ok, _ = await delete_category(cat_name, tele_user_id)
    cats = await get_categories(tele_user_id)
    if ok:
        from bot.responses import category_remove_success

        await query.edit_message_text(
            category_remove_success(cat_name),
            reply_markup=category_menu_keyboard(True),
        )
    else:
        await query.edit_message_text(
            categories_list(cats),
            parse_mode="HTML",
            reply_markup=category_menu_keyboard(True),
        )
    return State.IDLE


@require_auth
async def cb_back_category_manager(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    tele_user_id = update.effective_user.id
    cats = await get_categories(tele_user_id)
    await query.edit_message_text(
        categories_list(cats),
        parse_mode="HTML",
        reply_markup=category_menu_keyboard(is_admin(tele_user_id)),
    )
    return State.IDLE


@require_auth
async def cb_main_menu(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        welcome(), parse_mode="HTML", reply_markup=welcome_keyboard()
    )
    return State.IDLE
