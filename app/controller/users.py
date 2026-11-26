from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controller.deps import get_current_user
from app.model.models import User
from app.repository.user_repo import UserRepository
from app.schema.auth import UserOut
from app.schema.common import ErrorOut
from app.schema.user import UserUpdateIn

router = APIRouter(prefix="/users", tags=["Профиль"])


@router.get(
    "/me",
    response_model=UserOut,
    summary="Профиль текущего пользователя",
    responses={401: {"model": ErrorOut}},
)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Обновление профиля (имя, дата рождения, хронотип)",
    responses={401: {"model": ErrorOut}},
)
def update_me(
    payload: UserUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    updated = UserRepository.update(
        db,
        current_user,
        name=payload.name.strip() if payload.name is not None else None,
        birth_date=payload.birth_date,
        chronotype=payload.chronotype.value if payload.chronotype is not None else None,
    )
    return UserOut.model_validate(updated)
