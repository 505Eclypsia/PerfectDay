import datetime as dt
import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.model.enums import BiorhythmCycle, SlotStatus, TaskType
from app.schema.biorhythm import BiorhythmValuesOut

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):(00|30)$")


def _validate_hhmm_grid(value: str) -> str:
    if not _HHMM_RE.match(value):
        raise ValueError("Время должно быть в формате HH:MM и кратно 30 минутам.")
    h, m = map(int, value.split(":"))
    total = h * 60 + m
    if total < 8 * 60 or total > 22 * 60:
        raise ValueError("Время слота должно находиться в пределах 08:00–22:00.")
    return value


class ScheduleGenerateIn(BaseModel):
    date: dt.date = Field(examples=["2026-11-23"])


class SlotCreateIn(BaseModel):
    date: dt.date = Field(examples=["2026-11-23"])
    start_time: str = Field(examples=["13:00"])
    end_time: str = Field(examples=["14:00"])
    title: str = Field(min_length=1, max_length=200, examples=["Обед"])
    type: TaskType = Field(default=TaskType.REST, examples=[TaskType.REST])

    @field_validator("start_time", "end_time")
    @classmethod
    def check_grid(cls, v: str) -> str:
        return _validate_hhmm_grid(v)


class SlotUpdateIn(BaseModel):
    start_time: Optional[str] = Field(default=None, examples=["15:00"])
    end_time: Optional[str] = Field(default=None, examples=["17:00"])
    status: Optional[SlotStatus] = Field(default=None, examples=[SlotStatus.DONE])

    @field_validator("start_time", "end_time")
    @classmethod
    def check_grid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _validate_hhmm_grid(v)


class SlotOut(BaseModel):
    id: int
    task_id: Optional[int] = None
    title: str
    type: TaskType
    start_time: str = Field(examples=["11:00"])
    end_time: str = Field(examples=["13:00"])
    status: SlotStatus
    is_fixed: bool
    reason: Optional[str] = None
    warning: Optional[str] = None


class UnplacedTaskOut(BaseModel):
    id: Optional[int] = None
    title: str


class DayPlanOut(BaseModel):
    date: dt.date
    biorhythms: BiorhythmValuesOut
    is_critical: bool
    critical_cycles: List[BiorhythmCycle]
    status: str = Field(examples=["Обычный день"])
    slots: List[SlotOut]
    unplaced: List[UnplacedTaskOut]
