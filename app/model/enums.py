from enum import Enum


class Chronotype(str, Enum):
    LARK = "lark"
    OWL = "owl"
    PIGEON = "pigeon"


class TaskType(str, Enum):
    INTELLECTUAL = "intellectual"
    PHYSICAL = "physical"
    CREATIVE = "creative"
    ROUTINE = "routine"
    REST = "rest"


class SlotStatus(str, Enum):
    PLANNED = "planned"
    DONE = "done"
    MISSED = "missed"
