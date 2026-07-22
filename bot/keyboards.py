from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def order_review_keyboard(idx: int, total: int) -> InlineKeyboardMarkup:
    """Keyboard for a single order review message."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{idx}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{idx}"),
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip:{idx}"),
        ],
    ])


def confirm_all_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm All", callback_data="confirm_all")],
    ])


def edit_field_keyboard(idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Name", callback_data=f"editfield:{idx}:name"),
            InlineKeyboardButton("Qty", callback_data=f"editfield:{idx}:quantity"),
        ],
        [
            InlineKeyboardButton("Price", callback_data=f"editfield:{idx}:price"),
            InlineKeyboardButton("Money", callback_data=f"editfield:{idx}:money"),
        ],
        [
            InlineKeyboardButton("Shop", callback_data=f"editfield:{idx}:shop"),
            InlineKeyboardButton("Category", callback_data=f"editfield:{idx}:category"),
        ],
        [
            InlineKeyboardButton("Notes", callback_data=f"editfield:{idx}:notes"),
            InlineKeyboardButton("« Back", callback_data=f"back:{idx}"),
        ],
    ])


def category_select_keyboard(idx: int, categories: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i:i + 2]:
            row.append(InlineKeyboardButton(cat, callback_data=f"setcat:{idx}:{cat}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back", callback_data=f"edit:{idx}")])
    return InlineKeyboardMarkup(rows)
