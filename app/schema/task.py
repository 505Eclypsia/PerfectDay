from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.model.enums import TaskStatus

TaskCategory = Literal["intellectual", "physical", "creative", "routine"]


def _validate_recurrence(days: Optional[List[int]]) -> Optional[List[int]]:
    if days is None:
        return None
    for d in days:
        if d < 0 or d > 6:
            raise ValueError("Дни повторения должны быть числами от 0 (пн) до 6 (вс).")
    unique_sorted = sorted(set(days))
    return unique_sorted or None


class TaskCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Подготовить отчёт"])
    type: TaskCategory = Field(examples=["intellectual"])
    duration_minutes: int = Field(ge=5, le=480, examples=[120])
    priority: int = Field(default=3, ge=1, le=5, examples=[4])
    description: Optional[str] = Field(default=None, max_length=2000)
    due_datetime: Optional[datetime] = Field(default=None, examples=["2026-11-27T18:00:00"])
    recurrence_days: Optional[List[int]] = Field(
        default=None,
        description="Список дней недели: 0 = понедельник ... 6 = воскресенье",
        examples=[[0, 2, 4]],
    )

    @field_validator("recurrence_days")
    @classmethod
    def check_recurrence(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        return _validate_recurrence(v)


class TaskUpdateIn(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    type: Optional[TaskCategory] = None
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=480)
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    description: Optional[str] = Field(default=None, max_length=2000)
    due_datetime: Optional[datetime] = None
    recurrence_days: Optional[List[int]] = None
    status: Optional[Literal["done", "not_done"]] = None

    @field_validator("recurrence_days")
    @classmethod
    def check_recurrence(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        return _validate_recurrence(v)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    type: TaskCategory
    duration_minutes: int
    priority: int
    due_datetime: Optional[datetime] = None
    recurrence_days: Optional[List[int]] = None
    status: TaskStatus
