from bot.i18n import _


def welcome() -> str:
    return _("start.welcome")


def categories_list(cats) -> str:
    if not cats:
        return _("categories.none")
    lines = []
    for c in cats:
        marker = "•" if c.is_default else "◦"
        lines.append(f"{marker} {c.name}")
    return _("categories.title") + "\n".join(lines)


def categories_none() -> str:
    return _("categories.none")


def addcat_usage() -> str:
    return _("addcat.usage")


def delcat_usage() -> str:
    return _("delcat.usage")


def history_list(orders) -> str:
    if not orders:
        return _("history.none")
    lines = []
    for o in orders:
        icon = _("source." + o.payment_source)
        lines.append(f"{icon} {o.date} | {o.name} | {o.money:,}₫ | {o.category_name}")
    return _("history.title") + "\n".join(lines)


def history_none() -> str:
    return _("history.none")


def export_all_synced() -> str:
    return _("export.all_synced")


def export_syncing(n: int) -> str:
    return _("export.syncing", n=n)


def export_synced(n: int) -> str:
    return _("export.synced", n=n)


def export_failed(err: str) -> str:
    return _("export.failed", err=err)


def processing() -> str:
    return _("image.processing")


def not_image() -> str:
    return _("image.not_image")


def no_orders() -> str:
    return _("image.no_orders")


def found_orders(n: int) -> str:
    return _("image.found_orders", n=n)


def session_expired() -> str:
    return _("session.expired")


def session_expired_short() -> str:
    return _("session.expired_short")


def already_processed() -> str:
    return _("order.already_processed")


def saved_line(saved_suffix: str) -> str:
    return _("order.saved") + saved_suffix


def saved_count_line(n: int, saved_suffix: str) -> str:
    return _("order.saved_count", n=n) + saved_suffix


def synced_suffix() -> str:
    return _("order.synced")


def saved_local_suffix() -> str:
    return _("order.saved_local")


def skipped() -> str:
    return _("order.skipped")


def nothing_to_confirm() -> str:
    return _("order.nothing_to_confirm")


def which_field() -> str:
    return _("order.which_field")


def choose_category() -> str:
    return _("order.choose_category")


def enter_field(field_name: str) -> str:
    return _("order.enter_field", field=_("field." + field_name))


def edit_nothing() -> str:
    return _("edit.nothing")


def edit_invalid() -> str:
    return _("edit.invalid")


def fmt_order(order, idx: int, total: int) -> str:
    icon = _("source." + order.extracted.payment_source)
    notes_line = _("order.notes_fmt", notes=order.notes) if order.notes else ""
    return _(
        "order.format",
        idx=idx + 1,
        total=total,
        icon=icon,
        name=order.extracted.name,
        money=order.extracted.money,
        shop=order.extracted.shop,
        source=order.extracted.payment_source,
        category=order.category_name,
        notes_line=notes_line,
    )


def language_set(code: str) -> str:
    return _("language.set", lang=_("language.name." + code))


def language_invalid(langs: str) -> str:
    return _("language.invalid", langs=langs)
