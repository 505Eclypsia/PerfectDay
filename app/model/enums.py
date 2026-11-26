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


class TaskStatus(str, Enum):
    NOT_DONE = "not_done"
    ON_REPEAT = "on_repeat"
    DONE = "done"


class SlotStatus(str, Enum):
    PLANNED = "planned"
    DONE = "done"
    MISSED = "missed"


class BiorhythmCycle(str, Enum):
    PHYSICAL = "physical"
    EMOTIONAL = "emotional"
    INTELLECTUAL = "intellectual"
