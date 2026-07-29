from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import _


def _main_menu_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton(_("keyboard.main_menu"), callback_data="main_menu")


def _back_category_manager_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton(
        _("keyboard.back_category_manager"), callback_data="back_category_manager"
    )


def order_review_keyboard(idx: int, total: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.confirm"), callback_data=f"confirm:{idx}"
                ),
                InlineKeyboardButton(_("keyboard.edit"), callback_data=f"edit:{idx}"),
                InlineKeyboardButton(_("keyboard.skip"), callback_data=f"skip:{idx}"),
            ],
            [_main_menu_btn()],
        ]
    )


def confirm_all_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.confirm_all"), callback_data="confirm_all"
                )
            ],
            [_main_menu_btn()],
        ]
    )


def edit_field_keyboard(idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.name"), callback_data=f"editfield:{idx}:name"
                ),
                InlineKeyboardButton(
                    _("keyboard.money"), callback_data=f"editfield:{idx}:money"
                ),
            ],
            [
                InlineKeyboardButton(
                    _("keyboard.shop"), callback_data=f"editfield:{idx}:shop"
                ),
                InlineKeyboardButton(
                    _("keyboard.category"), callback_data=f"editfield:{idx}:category"
                ),
            ],
            [
                InlineKeyboardButton(
                    _("keyboard.notes"), callback_data=f"editfield:{idx}:notes"
                ),
                InlineKeyboardButton(_("keyboard.back"), callback_data=f"back:{idx}"),
            ],
            [_main_menu_btn()],
        ]
    )


def category_select_keyboard(idx: int, categories: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i : i + 2]:
            row.append(InlineKeyboardButton(cat, callback_data=f"setcat:{idx}:{cat}"))
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(_("keyboard.back"), callback_data=f"edit:{idx}"),
            _main_menu_btn(),
        ]
    )
    return InlineKeyboardMarkup(rows)


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.categories"), callback_data="welcome_categories"
                ),
                InlineKeyboardButton(
                    _("keyboard.history"), callback_data="welcome_history"
                ),
            ],
            [
                InlineKeyboardButton(
                    _("keyboard.users"), callback_data="welcome_users"
                ),
                InlineKeyboardButton(
                    _("keyboard.language"), callback_data="welcome_language"
                ),
            ],
        ]
    )


def category_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_admin:
        buttons.append(
            InlineKeyboardButton(_("keyboard.cat_add"), callback_data="cat_add")
        )
        buttons.append(
            InlineKeyboardButton(_("keyboard.cat_remove"), callback_data="cat_remove")
        )
        buttons.append(
            InlineKeyboardButton(_("keyboard.cat_edit"), callback_data="cat_edit")
        )
    rows = [[b] for b in buttons]
    rows.append([_main_menu_btn()])
    return InlineKeyboardMarkup(rows)


def category_remove_keyboard(categories) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        if not cat.is_default:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"❌ {cat.name}", callback_data=f"cat_rm:{cat.name}"
                    )
                ]
            )
    rows.append([_back_category_manager_btn(), _main_menu_btn()])
    return InlineKeyboardMarkup(rows)


def language_keyboard() -> InlineKeyboardMarkup:
    from bot.i18n import get_available_locales

    locales = get_available_locales()
    rows = [
        [InlineKeyboardButton(_("language.name." + code), callback_data=f"lang:{code}")]
        for code in locales
    ]
    rows.append([_main_menu_btn()])
    return InlineKeyboardMarkup(rows)


def main_menu_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_main_menu_btn()]])


def back_to_category_manager_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_back_category_manager_btn(), _main_menu_btn()]])


def history_export_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.export"), callback_data="history_export"
                )
            ],
            [_main_menu_btn()],
        ]
    )


def user_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if is_admin:
        buttons.append(
            InlineKeyboardButton(_("keyboard.user_add"), callback_data="user_add")
        )
        buttons.append(
            InlineKeyboardButton(_("keyboard.user_remove"), callback_data="user_remove")
        )
    rows = [[b] for b in buttons] if buttons else []
    rows.append([_main_menu_btn()])
    return InlineKeyboardMarkup(rows)
