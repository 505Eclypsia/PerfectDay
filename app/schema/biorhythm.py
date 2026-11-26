import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field

from app.model.enums import BiorhythmCycle


class BiorhythmValuesOut(BaseModel):
    physical: float = Field(examples=[-39.8])
    emotional: float = Field(examples=[100.0])
    intellectual: float = Field(examples=[-61.8])


class DayNoteOut(BaseModel):
    window: Optional[str] = Field(default=None, examples=["18:00-21:00"])
    text: str = Field(
        examples=["Интеллект на спаде (-61.8%). Интеллектуальный блок переключён в режим лёгкой рутины."]
    )


class BiorhythmDayOut(BaseModel):
    date: dt.date
    values: BiorhythmValuesOut
    is_critical: bool
    critical_cycles: List[BiorhythmCycle]
    status: str = Field(examples=["Обычный день"])
    notes: List[DayNoteOut]


class ForecastPointOut(BaseModel):
    date: dt.date
    values: BiorhythmValuesOut
    is_critical: bool
    critical_cycles: List[BiorhythmCycle]
