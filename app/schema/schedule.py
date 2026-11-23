from datetime import date, time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.model.enums import TaskType


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: TaskType
    duration_minutes: int = Field(gt=0, le=14 * 60)
    priority: int = Field(default=1, ge=1, le=5)
    fixed_start: Optional[time] = None


class SlotOut(BaseModel):
    start_time: time
    end_time: time
    title: str
    type: TaskType
    reason: str
    warning: Optional[str] = None


class DayNoteOut(BaseModel):
    text: str
    window: Optional[str] = None


class DayPlanOut(BaseModel):
    date: date
    biorhythms: Dict[str, float]
    is_critical: bool
    status: str
    notes: List[DayNoteOut]
    slots: List[SlotOut]
    unplaced: List[str]
