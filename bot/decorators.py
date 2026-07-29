import functools

from telegram import Update
from telegram.ext import ContextTypes

from bot.auth import is_authorized
from bot.states import State


def require_auth(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.effective_user is None or not await is_authorized(update.effective_user.id):
            if update.callback_query:
                await update.callback_query.answer()
            return State.IDLE
        return await func(update, context)
    return wrapper
