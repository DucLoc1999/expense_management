import logging

from telegram.ext import ApplicationBuilder

import config
from bot.auth import reload_users
from bot.i18n import load_locales, set_locale
from db.database import run_migrations
from bot.handlers import build_handlers, error_handler

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application) -> None:
    load_locales()
    set_locale(config.BOT_LOCALE)
    await run_migrations()
    await reload_users()
    logger.info("Locale set to '%s'. Database initialised.", config.BOT_LOCALE)


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
