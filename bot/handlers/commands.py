from telegram import Update
from telegram.ext import ContextTypes

import config
from bot.decorators import require_auth
from bot.responses import (
    welcome,
    categories_list,
    addcat_usage,
    delcat_usage,
    history_list,
    export_failed,
    language_set,
    language_invalid,
)
from bot.keyboards import welcome_keyboard
from bot.states import State
from db.models import (
    get_categories,
    add_category,
    delete_category,
    get_recent_orders,
    get_unsynced_orders,
    mark_synced,
)
from services.sheets import append_orders, OrderRow


@require_auth
async def cmd_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        welcome(), parse_mode="Markdown", reply_markup=welcome_keyboard()
    )
    return State.IDLE


@require_auth
async def cmd_categories(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    cats = await get_categories()
    await update.message.reply_text(
        categories_list(cats), parse_mode="Markdown"
    )
    return State.IDLE


@require_auth
async def cmd_addcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args
    if not args:
        await update.message.reply_text(addcat_usage())
        return State.IDLE
    name = " ".join(args).strip()
    _, msg = await add_category(name)
    await update.message.reply_text(msg)
    return State.IDLE


@require_auth
async def cmd_delcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args
    if not args:
        await update.message.reply_text(delcat_usage())
        return State.IDLE
    name = " ".join(args).strip()
    _, msg = await delete_category(name)
    await update.message.reply_text(msg)
    return State.IDLE


@require_auth
async def cmd_history(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    orders = await get_recent_orders(update.effective_user.id, limit=5)
    await update.message.reply_text(
        history_list(orders), parse_mode="Markdown"
    )
    return State.IDLE


@require_auth
async def cmd_export(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    tele_user_id = update.effective_user.id
    sheet_url = f"https://docs.google.com/spreadsheets/d/{config.GOOGLE_SHEETS_ID}"
    unsynced = await get_unsynced_orders(tele_user_id)
    if not unsynced:
        await update.effective_message.reply_text(sheet_url)
        return State.IDLE
    rows = [
        OrderRow(
            date=o.date,
            name=o.name,
            money=o.money,
            shop=o.shop,
            category=o.category_name,
            notes=o.notes,
        )
        for o in unsynced
    ]
    ok, err = await append_orders(rows, tele_user_id)
    if ok:
        await mark_synced([o.id for o in unsynced])
        await update.effective_message.reply_text(sheet_url)
    else:
        await update.effective_message.reply_text(export_failed(err or ""))
    return State.IDLE


@require_auth
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
