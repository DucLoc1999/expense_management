import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from telegram import Update, Message
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import config
from bot.keyboards import (
    order_review_keyboard,
    confirm_all_keyboard,
    edit_field_keyboard,
    category_select_keyboard,
)
from bot.states import State
from db.models import (
    get_categories,
    add_category,
    delete_category,
    save_order,
    get_recent_orders,
    get_unsynced_orders,
    mark_synced,
    get_category_by_name,
)
from services.gemini import extract_orders, ExtractedOrder
from services.sheets import append_one, append_orders, OrderRow

logger = logging.getLogger(__name__)

# ── context.user_data keys ────────────────────────────────────────────────────
_PENDING = "pending_orders"      # list[PendingOrder]
_EDITING_IDX = "editing_idx"     # int
_EDITING_FIELD = "editing_field" # str


@dataclass
class PendingOrder:
    extracted: ExtractedOrder
    status: str = "pending"   # pending | confirmed | skipped
    category_name: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.category_name:
            self.category_name = self.extracted.suggested_category


# ── Access guard ──────────────────────────────────────────────────────────────

def _allowed(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id == config.ALLOWED_USER_ID


def _fmt_order(o: PendingOrder, idx: int, total: int) -> str:
    e = o.extracted
    src_icon = {"shopee": "🛍", "bank_transfer": "🏦", "other": "📄"}.get(e.payment_source, "📄")
    return (
        f"*Order {idx + 1}/{total}*\n"
        f"{src_icon} {e.name}\n"
        f"Qty: {e.quantity}   Price: {e.price:,}₫   Total: {e.money:,}₫\n"
        f"Shop: {e.shop}\n"
        f"Source: {e.payment_source}\n"
        f"Category: {o.category_name}"
        + (f"\nNotes: {o.notes}" if o.notes else "")
    )


# ── /start ─────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    await update.message.reply_text(
        "👋 *Expense Bot*\n\n"
        "Send me a screenshot of your payment bills and I'll extract expenses for you.\n\n"
        "*Commands:*\n"
        "/categories — list categories\n"
        "/addcat <name> — add category\n"
        "/delcat <name> — remove custom category\n"
        "/history — last 10 orders\n"
        "/export — sync unsynced orders to Google Sheet",
        parse_mode="Markdown",
    )
    return State.IDLE


# ── /categories ────────────────────────────────────────────────────────────────

async def cmd_categories(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    cats = await get_categories()
    if not cats:
        await update.message.reply_text("No categories found.")
        return State.IDLE
    lines = []
    for c in cats:
        marker = "•" if c.is_default else "◦"
        lines.append(f"{marker} {c.name}")
    await update.message.reply_text("*Categories:*\n" + "\n".join(lines), parse_mode="Markdown")
    return State.IDLE


# ── /addcat ────────────────────────────────────────────────────────────────────

async def cmd_addcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /addcat <category name>")
        return State.IDLE
    name = " ".join(args).strip()
    _, msg = await add_category(name)
    await update.message.reply_text(msg)
    return State.IDLE


# ── /delcat ────────────────────────────────────────────────────────────────────

async def cmd_delcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /delcat <category name>")
        return State.IDLE
    name = " ".join(args).strip()
    _, msg = await delete_category(name)
    await update.message.reply_text(msg)
    return State.IDLE


# ── /history ───────────────────────────────────────────────────────────────────

async def cmd_history(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    orders = await get_recent_orders(limit=10)
    if not orders:
        await update.message.reply_text("No orders saved yet.")
        return State.IDLE
    lines = []
    for o in orders:
        src_icon = {"shopee": "🛍", "bank_transfer": "🏦", "other": "📄"}.get(o.payment_source, "📄")
        lines.append(
            f"{src_icon} {o.date} | {o.name} | {o.money:,}₫ | {o.category_name}"
        )
    await update.message.reply_text(
        "*Last 10 orders:*\n" + "\n".join(lines), parse_mode="Markdown"
    )
    return State.IDLE


# ── /export ────────────────────────────────────────────────────────────────────

async def cmd_export(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    unsynced = await get_unsynced_orders()
    if not unsynced:
        await update.message.reply_text("All orders are already synced.")
        return State.IDLE
    await update.message.reply_text(f"Syncing {len(unsynced)} order(s)...")
    rows = [
        OrderRow(
            date=o.date,
            name=o.name,
            quantity=o.quantity,
            price=o.price,
            money=o.money,
            shop=o.shop,
            category=o.category_name,
            notes=o.notes,
        )
        for o in unsynced
    ]
    ok, err = await append_orders(rows)
    if ok:
        await mark_synced([o.id for o in unsynced])
        await update.message.reply_text(f"Synced {len(unsynced)} order(s) to Google Sheet.")
    else:
        await update.message.reply_text(f"Sync failed: {err}\nOrders saved locally.")
    return State.IDLE


# ── Image reception ────────────────────────────────────────────────────────────

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE

    msg: Message = update.message
    processing = await msg.reply_text("Processing...")

    # Get file bytes
    if msg.photo:
        file = await msg.photo[-1].get_file()
        mime = "image/jpeg"
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        file = await msg.document.get_file()
        mime = msg.document.mime_type
    else:
        await processing.edit_text("Please send an image file.")
        return State.IDLE

    image_bytes = await file.download_as_bytearray()

    cats = await get_categories()
    cat_names = [c.name for c in cats]

    orders, error = await extract_orders(bytes(image_bytes), mime, cat_names)

    if error or not orders:
        await processing.edit_text(error or "No orders found.")
        return State.IDLE

    pending = [PendingOrder(extracted=o) for o in orders]
    context.user_data[_PENDING] = pending

    await processing.delete()

    # Send one message per order
    for i, po in enumerate(pending):
        await msg.reply_text(
            _fmt_order(po, i, len(pending)),
            parse_mode="Markdown",
            reply_markup=order_review_keyboard(i, len(pending)),
        )

    if len(pending) > 1:
        await msg.reply_text(
            f"Found {len(pending)} orders. Review each or:",
            reply_markup=confirm_all_keyboard(),
        )

    return State.IDLE


# ── Callback: confirm single ───────────────────────────────────────────────────

async def cb_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text("Session expired. Please send the image again.")
        return State.IDLE

    po = pending[idx]
    if po.status != "pending":
        await query.edit_message_text(_fmt_order(po, idx, len(pending)) + "\n\n_Already processed._", parse_mode="Markdown")
        return State.IDLE

    po.status = "confirmed"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cat = await get_category_by_name(po.category_name)
    if not cat:
        cat = await get_category_by_name("Khác")

    order_id = await save_order(
        name=po.extracted.name,
        quantity=po.extracted.quantity,
        price=po.extracted.price,
        money=po.extracted.money,
        shop=po.extracted.shop,
        category_id=cat.id,
        date=date_str,
        notes=po.notes,
        payment_source=po.extracted.payment_source,
    )

    row = OrderRow(
        date=date_str,
        name=po.extracted.name,
        quantity=po.extracted.quantity,
        price=po.extracted.price,
        money=po.extracted.money,
        shop=po.extracted.shop,
        category=po.category_name,
        payment_source=po.extracted.payment_source,
        notes=po.notes,
    )
    ok, _ = await append_one(row)
    if ok:
        await mark_synced([order_id])

    await query.edit_message_text(
        _fmt_order(po, idx, len(pending)) + "\n\n✅ Saved" + (" & synced." if ok else " locally (sync failed)."),
        parse_mode="Markdown",
    )
    return State.IDLE


# ── Callback: skip ─────────────────────────────────────────────────────────────

async def cb_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text("Session expired.")
        return State.IDLE

    pending[idx].status = "skipped"
    po = pending[idx]
    await query.edit_message_text(
        _fmt_order(po, idx, len(pending)) + "\n\n⏭ Skipped.",
        parse_mode="Markdown",
    )
    return State.IDLE


# ── Callback: confirm all ──────────────────────────────────────────────────────

async def cb_confirm_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])
    to_confirm = [po for po in pending if po.status == "pending"]

    if not to_confirm:
        await query.edit_message_text("Nothing to confirm.")
        return State.IDLE

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    order_ids = []
    rows = []

    for po in to_confirm:
        po.status = "confirmed"
        cat = await get_category_by_name(po.category_name)
        if not cat:
            cat = await get_category_by_name("Khác")
        oid = await save_order(
            name=po.extracted.name,
            quantity=po.extracted.quantity,
            price=po.extracted.price,
            money=po.extracted.money,
            shop=po.extracted.shop,
            category_id=cat.id,
            date=date_str,
            notes=po.notes,
            payment_source=po.extracted.payment_source,
        )
        order_ids.append(oid)
        rows.append(OrderRow(
            date=date_str,
            name=po.extracted.name,
            quantity=po.extracted.quantity,
            price=po.extracted.price,
            money=po.extracted.money,
            shop=po.extracted.shop,
            category=po.category_name,
            payment_source=po.extracted.payment_source,
            notes=po.notes,
        ))

    ok, _ = await append_orders(rows)
    if ok:
        await mark_synced(order_ids)

    n = len(to_confirm)
    await query.edit_message_text(
        f"✅ Saved {n} order(s)" + (" & synced." if ok else " locally (sync failed).")
    )
    return State.IDLE


# ── Callback: edit (show field selector) ──────────────────────────────────────

async def cb_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text("Session expired.")
        return State.IDLE

    context.user_data[_EDITING_IDX] = idx
    po = pending[idx]
    await query.edit_message_text(
        _fmt_order(po, idx, len(pending)) + "\n\nWhich field to edit?",
        parse_mode="Markdown",
        reply_markup=edit_field_keyboard(idx),
    )
    return State.IDLE


# ── Callback: back to order review ────────────────────────────────────────────

async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    idx = int(query.data.split(":")[1])
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text("Session expired.")
        return State.IDLE

    po = pending[idx]
    await query.edit_message_text(
        _fmt_order(po, idx, len(pending)),
        parse_mode="Markdown",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE


# ── Callback: editfield — handle text fields or show category picker ───────────

async def cb_editfield(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")   # editfield:<idx>:<field>
    idx, field_name = int(parts[1]), parts[2]
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text("Session expired.")
        return State.IDLE

    if field_name == "category":
        cats = await get_categories()
        cat_names = [c.name for c in cats]
        await query.edit_message_text(
            "Choose a category:",
            reply_markup=category_select_keyboard(idx, cat_names),
        )
        return State.IDLE

    context.user_data[_EDITING_IDX] = idx
    context.user_data[_EDITING_FIELD] = field_name
    labels = {
        "name": "item name",
        "quantity": "quantity (number)",
        "price": "unit price (₫, number)",
        "money": "total paid (₫, number)",
        "shop": "shop name",
        "notes": "notes",
    }
    await query.edit_message_text(f"Enter new {labels.get(field_name, field_name)}:")
    return State.EDITING_FIELD_INPUT


# ── Callback: setcat ───────────────────────────────────────────────────────────

async def cb_setcat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await update.callback_query.answer()
        return State.IDLE

    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 2)   # setcat:<idx>:<catname>
    idx, cat_name = int(parts[1]), parts[2]
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx >= len(pending):
        await query.edit_message_text("Session expired.")
        return State.IDLE

    pending[idx].category_name = cat_name
    po = pending[idx]
    await query.edit_message_text(
        _fmt_order(po, idx, len(pending)),
        parse_mode="Markdown",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE


# ── Text input for field editing ───────────────────────────────────────────────

async def handle_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE

    idx = context.user_data.get(_EDITING_IDX)
    field_name = context.user_data.get(_EDITING_FIELD)
    pending: list[PendingOrder] = context.user_data.get(_PENDING, [])

    if idx is None or field_name is None or idx >= len(pending):
        await update.message.reply_text("Nothing to edit. Please send a screenshot first.")
        return State.IDLE

    text = update.message.text.strip()
    po = pending[idx]
    e = po.extracted

    try:
        if field_name == "name":
            e.name = text
        elif field_name == "quantity":
            e.quantity = int(text)
        elif field_name == "price":
            e.price = int(text.replace(",", "").replace(".", ""))
        elif field_name == "money":
            e.money = int(text.replace(",", "").replace(".", ""))
        elif field_name == "shop":
            e.shop = text
        elif field_name == "notes":
            po.notes = text
    except ValueError:
        await update.message.reply_text("Invalid value. Please enter a valid number.")
        return State.EDITING_FIELD_INPUT

    context.user_data.pop(_EDITING_FIELD, None)
    context.user_data.pop(_EDITING_IDX, None)

    await update.message.reply_text(
        _fmt_order(po, idx, len(pending)),
        parse_mode="Markdown",
        reply_markup=order_review_keyboard(idx, len(pending)),
    )
    return State.IDLE


# ── Handler for adding category via free text (ADDING_CATEGORY state) ──────────

async def handle_addcat_input(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return State.IDLE
    name = update.message.text.strip()
    _, msg = await add_category(name)
    await update.message.reply_text(msg)
    return State.IDLE


# ── Build handler list ─────────────────────────────────────────────────────────

def build_handlers():
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("categories", cmd_categories),
        CommandHandler("addcat", cmd_addcat),
        CommandHandler("delcat", cmd_delcat),
        CommandHandler("history", cmd_history),
        CommandHandler("export", cmd_export),
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
