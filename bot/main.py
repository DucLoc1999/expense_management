import logging

from telegram.ext import ApplicationBuilder

import config
from db.database import init_db
from bot.handlers import build_handlers

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application) -> None:
    await init_db()
    logger.info("Database initialised.")


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    for handler in build_handlers():
        app.add_handler(handler)

    logger.info("Bot starting (polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
