import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from bot.handlers.commands import (
    cmd_start,
    cmd_categories,
    cmd_addcat,
    cmd_delcat,
    cmd_history,
    cmd_language,
    cmd_users,
    cmd_adduser,
    cmd_removeuser,
)
from bot.handlers.image import handle_image
from bot.handlers.callbacks import (
    cb_confirm,
    cb_skip,
    cb_confirm_all,
    cb_edit,
    cb_back,
    cb_editfield,
    cb_setcat,
    cb_welcome_categories,
    cb_welcome_history,
    cb_welcome_language,
    cb_welcome_users,
    cb_user_add,
    cb_user_remove,
    cb_cat_add,
    cb_cat_edit,
    cb_cat_remove,
    cb_cat_rm,
    cb_cat_list,
    cb_language_set,
    cb_main_menu,
    cb_back_category_manager,
)
from bot.handlers.text import handle_field_input

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "An unexpected error occurred. Please try again."
            )
        except Exception:
            pass


def build_handlers():
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("categories", cmd_categories),
        CommandHandler("addcat", cmd_addcat),
        CommandHandler("delcat", cmd_delcat),
        CommandHandler("history", cmd_history),
        CommandHandler("language", cmd_language),
        CommandHandler("users", cmd_users),
        CommandHandler("adduser", cmd_adduser),
        CommandHandler("removeuser", cmd_removeuser),
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image),
        CallbackQueryHandler(cb_confirm, pattern=r"^confirm:\d+$"),
        CallbackQueryHandler(cb_skip, pattern=r"^skip:\d+$"),
        CallbackQueryHandler(cb_confirm_all, pattern=r"^confirm_all$"),
        CallbackQueryHandler(cb_edit, pattern=r"^edit:\d+$"),
        CallbackQueryHandler(cb_back, pattern=r"^back:\d+$"),
        CallbackQueryHandler(cb_editfield, pattern=r"^editfield:\d+:\w+$"),
        CallbackQueryHandler(cb_setcat, pattern=r"^setcat:\d+:.+$"),
        CallbackQueryHandler(cb_welcome_categories, pattern=r"^welcome_categories$"),
        CallbackQueryHandler(cb_welcome_history, pattern=r"^welcome_history$"),
        CallbackQueryHandler(cb_welcome_language, pattern=r"^welcome_language$"),
        CallbackQueryHandler(cb_welcome_users, pattern=r"^welcome_users$"),
        CallbackQueryHandler(cb_user_add, pattern=r"^user_add$"),
        CallbackQueryHandler(cb_user_remove, pattern=r"^user_remove$"),
        CallbackQueryHandler(cb_cat_add, pattern=r"^cat_add$"),
        CallbackQueryHandler(cb_cat_edit, pattern=r"^cat_edit$"),
        CallbackQueryHandler(cb_cat_remove, pattern=r"^cat_remove$"),
        CallbackQueryHandler(cb_cat_rm, pattern=r"^cat_rm:.+$"),
        CallbackQueryHandler(cb_cat_list, pattern=r"^cat_list$"),
        CallbackQueryHandler(cb_language_set, pattern=r"^lang:\w+$"),
        CallbackQueryHandler(cb_main_menu, pattern=r"^main_menu$"),
        CallbackQueryHandler(
            cb_back_category_manager, pattern=r"^back_category_manager$"
        ),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_input),
    ]
