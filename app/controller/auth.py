from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.repository.user_repo import UserRepository
from app.schema.auth import AuthRegisterOut, RegisterIn, TokenOut, UserOut
from app.schema.common import ErrorOut
from app.service.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    "/register",
    response_model=AuthRegisterOut,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    responses={409: {"model": ErrorOut, "description": "Email уже зарегистрирован"}},
)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> AuthRegisterOut:
    existing = UserRepository.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует.",
        )

    user = UserRepository.create(
        db=db,
        name=payload.name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        birth_date=payload.birth_date,
        chronotype=payload.chronotype.value,
    )
    token = create_access_token(user.id)
    return AuthRegisterOut(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Вход по email и паролю (OAuth2)",
    responses={401: {"model": ErrorOut, "description": "Неверный email или пароль"}},
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenOut:
    user = UserRepository.get_by_email(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.id)
    return TokenOut(access_token=token, token_type="bearer")
