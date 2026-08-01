from datetime import datetime, timezone

from bot.i18n import _
from bot.models import PendingOrder
from db.models import get_category_by_name, save_bill


async def confirm_order(po: PendingOrder, tele_user_id: int) -> int:
    """Confirm a single order: resolve category and save to DB.

    Returns the new bill id.
    """
    po.status = "confirmed"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cat = await get_category_by_name(po.category_name, tele_user_id)
    if not cat:
        cat = await get_category_by_name(_("category.other"), tele_user_id)

    return await save_bill(
        name=po.extracted.name,
        money=po.extracted.money,
        shop=po.extracted.shop,
        category_id=cat.id,
        date=date_str,
        notes=po.notes,
        payment_source=po.extracted.payment_source,
        tele_user_id=tele_user_id,
    )


async def confirm_all_orders(pending: list[PendingOrder], tele_user_id: int) -> int:
    """Confirm all pending orders in batch.

    Returns the count of confirmed bills.
    """
    to_confirm = [po for po in pending if po.status == "pending"]
    if not to_confirm:
        return 0

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for po in to_confirm:
        po.status = "confirmed"
        cat = await get_category_by_name(po.category_name, tele_user_id)
        if not cat:
            cat = await get_category_by_name(_("category.other"), tele_user_id)
        await save_bill(
            name=po.extracted.name,
            money=po.extracted.money,
            shop=po.extracted.shop,
            category_id=cat.id,
            date=date_str,
            notes=po.notes,
            payment_source=po.extracted.payment_source,
            tele_user_id=tele_user_id,
        )

    return len(to_confirm)
