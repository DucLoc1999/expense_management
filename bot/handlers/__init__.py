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
    cmd_export,
    cmd_language,
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
)
from bot.handlers.text import handle_field_input, handle_addcat_input

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
        CommandHandler("export", cmd_export),
        CommandHandler("language", cmd_language),
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image),
        CallbackQueryHandler(cb_confirm, pattern=r"^confirm:\d+$"),
        CallbackQueryHandler(cb_skip, pattern=r"^skip:\d+$"),
        CallbackQueryHandler(cb_confirm_all, pattern=r"^confirm_all$"),
        CallbackQueryHandler(cb_edit, pattern=r"^edit:\d+$"),
        CallbackQueryHandler(cb_back, pattern=r"^back:\d+$"),
        CallbackQueryHandler(cb_editfield, pattern=r"^editfield:\d+:\w+$"),
        CallbackQueryHandler(cb_setcat, pattern=r"^setcat:\d+:.+$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_input),
    ]
