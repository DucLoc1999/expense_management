from telegram import Update
from telegram.ext import ContextTypes

from bot.decorators import require_auth
from bot.models import PendingOrder, _PENDING
from bot.responses import (
    processing,
    not_image,
    no_orders,
    found_orders,
    fmt_order,
)
from bot.keyboards import order_review_keyboard, confirm_all_keyboard
from bot.states import State
from db.models import get_categories
from services.gemini import extract_orders


@require_auth
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    processing_msg = await msg.reply_text(processing())

    if msg.photo:
        file = await msg.photo[-1].get_file()
        mime = "image/jpeg"
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        file = await msg.document.get_file()
        mime = msg.document.mime_type
    else:
        await processing_msg.edit_text(not_image())
        return State.IDLE

    image_bytes = await file.download_as_bytearray()

    cats = await get_categories()
    cat_names = [c.name for c in cats]

    orders, error = await extract_orders(bytes(image_bytes), mime, cat_names)

    if error or not orders:
        await processing_msg.edit_text(error or no_orders())
        return State.IDLE

    pending = [PendingOrder(extracted=o) for o in orders]
    context.user_data[_PENDING] = pending

    await processing_msg.delete()

    for i, po in enumerate(pending):
        await msg.reply_text(
            fmt_order(po, i, len(pending)),
            parse_mode="Markdown",
            reply_markup=order_review_keyboard(i, len(pending)),
        )

    if len(pending) > 1:
        await msg.reply_text(
            found_orders(len(pending)),
            reply_markup=confirm_all_keyboard(),
        )

    return State.IDLE
