from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import _


def order_review_keyboard(idx: int, total: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_("keyboard.confirm"), callback_data=f"confirm:{idx}"),
            InlineKeyboardButton(_("keyboard.edit"), callback_data=f"edit:{idx}"),
            InlineKeyboardButton(_("keyboard.skip"), callback_data=f"skip:{idx}"),
        ],
    ])


def confirm_all_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_("keyboard.confirm_all"), callback_data="confirm_all")],
    ])


def edit_field_keyboard(idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_("keyboard.name"), callback_data=f"editfield:{idx}:name"),
            InlineKeyboardButton(_("keyboard.money"), callback_data=f"editfield:{idx}:money"),
        ],
        [
            InlineKeyboardButton(_("keyboard.shop"), callback_data=f"editfield:{idx}:shop"),
            InlineKeyboardButton(_("keyboard.category"), callback_data=f"editfield:{idx}:category"),
        ],
        [
            InlineKeyboardButton(_("keyboard.notes"), callback_data=f"editfield:{idx}:notes"),
            InlineKeyboardButton(_("keyboard.back"), callback_data=f"back:{idx}"),
        ],
    ])


def category_select_keyboard(idx: int, categories: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i:i + 2]:
            row.append(InlineKeyboardButton(cat, callback_data=f"setcat:{idx}:{cat}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(_("keyboard.back"), callback_data=f"edit:{idx}")])
    return InlineKeyboardMarkup(rows)
