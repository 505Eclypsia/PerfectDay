from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.model.enums import Chronotype


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Алексей"])
    email: EmailStr = Field(examples=["alex@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["StrongPass123"])
    birth_date: date = Field(examples=["2002-05-14"])
    chronotype: Chronotype = Field(examples=[Chronotype.OWL])

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Дата рождения не может быть в будущем.")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    birth_date: date
    chronotype: Chronotype


class AuthRegisterOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
