from datetime import datetime, timezone

from bot.models import PendingOrder
from db.models import get_category_by_name, save_order, mark_synced
from services.sheets import append_one, append_orders, OrderRow


async def confirm_order(po: PendingOrder, tele_user_id: int) -> tuple[bool, int]:
    """Confirm a single order: resolve category, save to DB, sync to Sheets.

    Returns (sheets_synced, order_id).
    """
    po.status = "confirmed"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cat = await get_category_by_name(po.category_name, tele_user_id)
    if not cat:
        cat = await get_category_by_name("Khác", tele_user_id)

    order_id = await save_order(
        name=po.extracted.name,
        money=po.extracted.money,
        shop=po.extracted.shop,
        category_id=cat.id,
        date=date_str,
        notes=po.notes,
        payment_source=po.extracted.payment_source,
        tele_user_id=tele_user_id,
    )

    row = OrderRow(
        date=date_str,
        name=po.extracted.name,
        money=po.extracted.money,
        shop=po.extracted.shop,
        category=po.category_name,
        payment_source=po.extracted.payment_source,
        notes=po.notes,
    )
    ok, _ = await append_one(row, tele_user_id)
    if ok:
        await mark_synced([order_id])

    return ok, order_id


async def confirm_all_orders(pending: list[PendingOrder], tele_user_id: int) -> tuple[bool, int]:
    """Confirm all pending orders in batch.

    Returns (sheets_synced, count_confirmed).
    """
    to_confirm = [po for po in pending if po.status == "pending"]
    if not to_confirm:
        return True, 0

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    order_ids = []
    rows = []

    for po in to_confirm:
        po.status = "confirmed"
        cat = await get_category_by_name(po.category_name, tele_user_id)
        if not cat:
            cat = await get_category_by_name("Khác", tele_user_id)
        oid = await save_order(
            name=po.extracted.name,
            money=po.extracted.money,
            shop=po.extracted.shop,
            category_id=cat.id,
            date=date_str,
            notes=po.notes,
            payment_source=po.extracted.payment_source,
            tele_user_id=tele_user_id,
        )
        order_ids.append(oid)
        rows.append(OrderRow(
            date=date_str,
            name=po.extracted.name,
            money=po.extracted.money,
            shop=po.extracted.shop,
            category=po.category_name,
            payment_source=po.extracted.payment_source,
            notes=po.notes,
        ))

    ok, _ = await append_orders(rows, tele_user_id)
    if ok:
        await mark_synced(order_ids)

    return ok, len(to_confirm)
