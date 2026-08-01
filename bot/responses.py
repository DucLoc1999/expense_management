import html

from bot.i18n import _, localized_name


def _esc(text) -> str:
    return html.escape(str(text))


def welcome() -> str:
    return _("start.welcome")


def categories_list(cats) -> str:
    if not cats:
        return _("categories.none")
    lines = []
    for c in cats:
        marker = "•" if c.is_system else "◦"
        lines.append(f"{marker} {_esc(localized_name(c.name, c.name_vi))}")
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
        name = _esc(o.name)
        cat = _esc(localized_name(o.category_name, o.category_name_vi))
        lines.append(f"{icon} <b>{name}</b>\n   {o.money:,}₫ · {cat} · {o.date}")
    return _("history.title") + "\n\n".join(lines)


def history_none() -> str:
    return _("history.none")


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


def saved_line() -> str:
    return _("order.saved")


def saved_count_line(n: int) -> str:
    return _("order.saved_count", n=n)


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
    notes_line = _("order.notes_fmt", notes=_esc(order.notes)) if order.notes else ""
    return _(
        "order.format",
        idx=idx + 1,
        total=total,
        icon=icon,
        name=_esc(order.extracted.name),
        money=order.extracted.money,
        shop=_esc(order.extracted.shop),
        source=_esc(order.extracted.payment_source),
        category=_esc(order.category_name),
        notes_line=notes_line,
    )


def language_set(code: str) -> str:
    return _("language.set", lang=_("language.name." + code))


def language_invalid(langs: str) -> str:
    return _("language.invalid", langs=langs)


def category_edit_prompt() -> str:
    return _("category.edit_prompt")


def category_menu_title() -> str:
    return _("category.menu_title")


def category_add_prompt() -> str:
    return _("category.add_prompt")


def category_remove_prompt() -> str:
    return _("category.remove_prompt")


def category_remove_success(name: str) -> str:
    return _("category.remove_success", name=name)


def category_remove_empty() -> str:
    return _("category.remove_empty")


def admin_denied() -> str:
    return _("admin.denied")


def admin_users_list(users: list[dict]) -> str:
    if not users:
        return _("admin.users_empty")
    parts = [_("admin.users_title")]
    for i, u in enumerate(users, 1):
        name = _esc(u["name"] or "-")
        role = _esc(u["role"] or "-")
        uid = u["tele_user_id"]
        parts.append(f"{i}. <code>{uid}</code> — {name} ({role})")
    return "\n".join(parts)


def admin_adduser_prompt() -> str:
    return _("admin.adduser.prompt")


def admin_removeuser_prompt() -> str:
    return _("admin.removeuser.prompt")


def admin_adduser_invalid() -> str:
    return _("admin.adduser.invalid")


def admin_adduser_done(tele_user_id: int) -> str:
    return _("admin.adduser.done", id=tele_user_id)


def admin_removeuser_done(tele_user_id: int) -> str:
    return _("admin.removeuser.done", id=tele_user_id)


def admin_adduser_usage() -> str:
    return _("admin.adduser.usage")


def admin_adduser_ok(tele_user_id: int, name: str, role: str) -> str:
    return _("admin.adduser.ok", id=tele_user_id, name=name or "-", role=role or "-")


def admin_removeuser_usage() -> str:
    return _("admin.removeuser.usage")


def admin_removeuser_ok(tele_user_id: int) -> str:
    return _("admin.removeuser.ok", id=tele_user_id)


def admin_removeuser_not_found(tele_user_id: int) -> str:
    return _("admin.removeuser.not_found", id=tele_user_id)
