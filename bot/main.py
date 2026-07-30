import logging

from telegram.ext import ApplicationBuilder, ContextTypes

import config
from bot.auth import reload_users
from bot.i18n import load_locales, set_locale
from db.database import run_migrations
from db.models import get_first_admin_id
from bot.handlers import build_handlers, error_handler
from services.system_monitor import get_system_info_text

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def send_system_info(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        admin_id = await get_first_admin_id()
        if admin_id is None:
            logger.warning("No admin found, skipping system info broadcast")
            return
        text = get_system_info_text()
        await context.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        logger.info("System info sent to admin %s", admin_id)
    except Exception:
        logger.exception("Failed to send system info")


async def post_init(application) -> None:
    load_locales()
    set_locale(config.BOT_LOCALE)
    await run_migrations()
    await reload_users()
    application.job_queue.run_repeating(send_system_info, interval=14400, first=60)
    logger.info("Locale set to '%s'. Database initialised. System monitor scheduled every 4h.", config.BOT_LOCALE)


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    for handler in build_handlers():
        app.add_handler(handler)
    app.add_error_handler(error_handler)

    logger.info("Bot starting (polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
