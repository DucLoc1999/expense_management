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
            [
                InlineKeyboardButton(
                    _("keyboard.expert"), callback_data="expert_open"
                ),
            ],
        ]
    )


EXPERT_PRESETS = [
    ("last_7", "expert.preset.last_7"),
    ("last_30", "expert.preset.last_30"),
    ("last_90", "expert.preset.last_90"),
    ("last_week", "expert.preset.last_week"),
    ("last_month", "expert.preset.last_month"),
    ("last_3_months", "expert.preset.last_3_months"),
    ("last_6_months", "expert.preset.last_6_months"),
]


def expert_screen_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.expert_filter"), callback_data="expert_filter"
                ),
                InlineKeyboardButton(
                    _("keyboard.expert_advice"), callback_data="expert_advice"
                ),
            ],
            [_main_menu_btn()],
        ]
    )


def expert_filter_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(EXPERT_PRESETS), 2):
        row = []
        for key, label in EXPERT_PRESETS[i : i + 2]:
            row.append(
                InlineKeyboardButton(_(label), callback_data=f"expert_preset:{key}")
            )
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(
                _("keyboard.expert_custom"), callback_data="expert_custom"
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                _("keyboard.expert_back"), callback_data="expert_back"
            ),
            _main_menu_btn(),
        ]
    )
    return InlineKeyboardMarkup(rows)


EXPERT_STARTER_KEYS = ["0", "1", "2", "3"]


def expert_starter_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(EXPERT_STARTER_KEYS), 2):
        row = []
        for key in EXPERT_STARTER_KEYS[i : i + 2]:
            row.append(
                InlineKeyboardButton(
                    _("expert.starter." + key),
                    callback_data=f"expert_starter:{key}",
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton(_("keyboard.expert_end"), callback_data="expert_end")])
    return InlineKeyboardMarkup(rows)


def expert_advisor_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _("keyboard.expert_end"), callback_data="expert_end"
                ),
            ]
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
        if not cat.is_system:
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
