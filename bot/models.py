from dataclasses import dataclass

from services.gemini import ExtractedOrder

_PENDING = "pending_orders"
_EDITING_IDX = "editing_idx"
_EDITING_FIELD = "editing_field"


@dataclass
class PendingOrder:
    extracted: ExtractedOrder
    status: str = "pending"
    category_name: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.category_name:
            self.category_name = self.extracted.suggested_category
