from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.model.enums import Chronotype


class UserUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    birth_date: Optional[date] = None
    chronotype: Optional[Chronotype] = None

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Дата рождения не может быть в будущем.")
        return v
