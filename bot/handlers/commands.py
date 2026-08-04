from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import is_admin, reload_users
from bot.decorators import require_auth
from bot.responses import (
    welcome,
    categories_list,
    addcat_usage,
    delcat_usage,
    history_list,
    language_set,
    language_invalid,
    admin_denied,
    admin_users_list,
    admin_adduser_usage,
    admin_adduser_ok,
    admin_removeuser_usage,
    admin_removeuser_ok,
    admin_removeuser_not_found,
)
from bot.keyboards import welcome_keyboard
from bot.states import State
from bot.models import _EXPERT_BUSY
from bot.expert import expert_guard, handle_expert_exit
from db.models import (
    get_categories,
    add_category,
    delete_category,
    get_recent_bills,
    add_tele_user,
    remove_tele_user,
    get_all_tele_users,
)


@require_auth
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await handle_expert_exit(update, context)
    context.user_data.pop(_EXPERT_BUSY, None)
    await update.message.reply_text(
        welcome(), parse_mode="HTML", reply_markup=welcome_keyboard()
    )
    return State.IDLE


@require_auth
@expert_guard
async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cats = await get_categories(update.effective_user.id)
    await update.message.reply_text(
        categories_list(cats), parse_mode="HTML"
    )
    return State.IDLE


@require_auth
@expert_guard
async def cmd_addcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args
    if not args:
        await update.message.reply_text(addcat_usage())
        return State.IDLE
    name = " ".join(args).strip()
    _, msg = await add_category(name, update.effective_user.id)
    await update.message.reply_text(msg)
    return State.IDLE


@require_auth
@expert_guard
async def cmd_delcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args
    if not args:
        await update.message.reply_text(delcat_usage())
        return State.IDLE
    name = " ".join(args).strip()
    _, msg = await delete_category(name, update.effective_user.id)
    await update.message.reply_text(msg)
    return State.IDLE


@require_auth
@expert_guard
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bills = await get_recent_bills(update.effective_user.id, limit=5)
    await update.message.reply_text(
        history_list(bills), parse_mode="HTML"
    )
    return State.IDLE


@require_auth
@expert_guard
async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from bot.i18n import set_locale, get_available_locales
    args = context.args
    langs = ", ".join(get_available_locales())
    if not args:
        await update.message.reply_text(language_invalid(langs))
        return State.IDLE
    code = args[0].strip().lower()
    if set_locale(code):
        await update.message.reply_text(language_set(code))
    else:
        await update.message.reply_text(language_invalid(langs))
    return State.IDLE


@require_auth
@expert_guard
async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(admin_denied())
        return State.IDLE
    users = await get_all_tele_users()
    await update.message.reply_text(admin_users_list(users), parse_mode="HTML")
    return State.IDLE


@require_auth
@expert_guard
async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(admin_denied())
        return State.IDLE
    args = context.args
    if not args:
        await update.message.reply_text(admin_adduser_usage())
        return State.IDLE
    try:
        tele_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text(admin_adduser_usage())
        return State.IDLE
    name = args[1] if len(args) > 1 else ""
    role = args[2] if len(args) > 2 else ""
    await add_tele_user(tele_user_id, name, role)
    await reload_users()
    await update.message.reply_text(admin_adduser_ok(tele_user_id, name, role))
    return State.IDLE


@require_auth
@expert_guard
async def cmd_removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(admin_denied())
        return State.IDLE
    args = context.args
    if not args:
        await update.message.reply_text(admin_removeuser_usage())
        return State.IDLE
    try:
        tele_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text(admin_removeuser_usage())
        return State.IDLE
    ok = await remove_tele_user(tele_user_id)
    if ok:
        await reload_users()
        await update.message.reply_text(admin_removeuser_ok(tele_user_id))
    else:
        await update.message.reply_text(admin_removeuser_not_found(tele_user_id))
    return State.IDLE
