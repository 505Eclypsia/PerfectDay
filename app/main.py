from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database import Base, engine
from app.config.settings import get_settings
from app.controller import auth, biorhythms, schedule, tasks, users
from app.model import models  # noqa: F401 — регистрирует ORM-модели в Base.metadata

settings = get_settings()

TAGS_METADATA = [
    {
        "name": "Авторизация",
        "description": "Регистрация и вход по JWT Bearer-токену (срок жизни 24 часа).",
    },
    {
        "name": "Профиль",
        "description": "Просмотр и обновление профиля, даты рождения и хронотипа.",
    },
    {
        "name": "Биоритмы",
        "description": "Расчёт трёх циклов (23/28/33 дня), критических дней, рекомендаций и прогноза.",
    },
    {
        "name": "Задачи",
        "description": "Управление бэклогом разовых и регулярных задач.",
    },
    {
        "name": "Расписание",
        "description": "Генерация таймлайна дня, ручные слоты, перенос и отметка выполнения.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "REST API интеллектуального биоритмического планировщика «Идеальный День». "
        "Все защищённые эндпоинты принимают заголовок `Authorization: Bearer <token>`."
    ),
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(biorhythms.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)
app.include_router(schedule.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Система"], summary="Проверка доступности сервиса")
def healthcheck():
    return {"status": "ok"}
