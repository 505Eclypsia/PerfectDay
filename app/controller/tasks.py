from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controller.deps import get_current_user
from app.model.enums import TaskStatus
from app.model.models import User
from app.repository.task_repo import TaskRepository
from app.schema.common import ErrorOut
from app.schema.task import TaskCreateIn, TaskOut, TaskUpdateIn

router = APIRouter(prefix="/tasks", tags=["Задачи"])


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать задачу в бэклоге",
    responses={401: {"model": ErrorOut}},
)
def create_task(
    payload: TaskCreateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task_status = (
        TaskStatus.ON_REPEAT.value
        if payload.recurrence_days
        else TaskStatus.NOT_DONE.value
    )
    task = TaskRepository.create(
        db=db,
        user_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        type=payload.type,
        priority=payload.priority,
        due_datetime=payload.due_datetime,
        recurrence_days=payload.recurrence_days,
        status=task_status,
    )
    return TaskOut.model_validate(task)


@router.get(
    "",
    response_model=List[TaskOut],
    summary="Список задач пользователя",
    responses={401: {"model": ErrorOut}},
)
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TaskOut]:
    tasks = TaskRepository.list_by_user(db, current_user.id, status=status_filter)
    return [TaskOut.model_validate(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=TaskOut,
    summary="Получить задачу по ID",
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = TaskRepository.get_by_id_and_user(db, task_id, current_user.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена.",
        )
    return TaskOut.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskOut,
    summary="Частично обновить задачу",
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def update_task(
    task_id: int,
    payload: TaskUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = TaskRepository.get_by_id_and_user(db, task_id, current_user.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is not None:
        updates["title"] = updates["title"].strip()

    if "recurrence_days" in updates:
        if updates["recurrence_days"]:
            updates["status"] = TaskStatus.ON_REPEAT.value
        elif "status" not in updates and task.status == TaskStatus.ON_REPEAT.value:
            updates["status"] = TaskStatus.NOT_DONE.value

    updated = TaskRepository.update(db, task, updates)
    return TaskOut.model_validate(updated)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить задачу из бэклога",
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    task = TaskRepository.get_by_id_and_user(db, task_id, current_user.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена.",
        )
    TaskRepository.delete(db, task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
