from dataclasses import dataclass

from services.gemini import ExtractedOrder

_PENDING = "pending_orders"
_EDITING_IDX = "editing_idx"
_EDITING_FIELD = "editing_field"
_EXPERT_FILTER = "expert_filter"
_EXPERT_SESSION = "expert_session"
_EXPERT_MODE = "expert_mode"
_EXPERT_BUSY = "expert_busy"
_EXPERT_CONTEXT = "expert_context"


@dataclass
class PendingOrder:
    extracted: ExtractedOrder
    status: str = "pending"
    category_name: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.category_name:
            self.category_name = self.extracted.suggested_category
