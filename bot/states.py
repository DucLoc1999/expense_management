from enum import IntEnum, auto


class State(IntEnum):
    IDLE = auto()
    ADDING_CATEGORY = auto()
    DELETING_CATEGORY = auto()
    EDITING_FIELD = auto()
    EDITING_FIELD_INPUT = auto()
    EDITING_CATEGORIES = auto()
