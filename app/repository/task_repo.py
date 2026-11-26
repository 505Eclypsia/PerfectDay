from typing import List, Optional

from sqlalchemy.orm import Session

from app.model.enums import SlotStatus, TaskStatus
from app.model.models import ScheduleSlot, Task


class TaskRepository:
    @staticmethod
    def create(db: Session, user_id: int, **fields) -> Task:
        task = Task(user_id=user_id, **fields)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def list_by_user(
        db: Session, user_id: int, status: Optional[TaskStatus] = None
    ) -> List[Task]:
        q = db.query(Task).filter(Task.user_id == user_id)
        if status is not None:
            q = q.filter(Task.status == status.value)
        return q.order_by(Task.created_at.desc(), Task.id.desc()).all()

    @staticmethod
    def get_by_id_and_user(
        db: Session, task_id: int, user_id: int
    ) -> Optional[Task]:
        return (
            db.query(Task)
            .filter(Task.id == task_id, Task.user_id == user_id)
            .first()
        )

    @staticmethod
    def list_active_for_date(db: Session, user_id: int, weekday: int) -> List[Task]:
        tasks = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.status.in_([TaskStatus.NOT_DONE.value, TaskStatus.ON_REPEAT.value]),
            )
            .all()
        )
        result: List[Task] = []
        for task in tasks:
            if task.status == TaskStatus.NOT_DONE.value:
                result.append(task)
            elif task.status == TaskStatus.ON_REPEAT.value:
                if task.recurrence_days and weekday in task.recurrence_days:
                    result.append(task)
        return result

    @staticmethod
    def update(db: Session, task: Task, fields: dict) -> Task:
        for key, value in fields.items():
            setattr(task, key, value)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete(db: Session, task: Task) -> None:
        # Запланированные слоты удаляются, выполненные и пропущенные остаются в истории (task_id = NULL)
        (
            db.query(ScheduleSlot)
            .filter(
                ScheduleSlot.task_id == task.id,
                ScheduleSlot.status == SlotStatus.PLANNED.value,
            )
            .delete(synchronize_session=False)
        )
        (
            db.query(ScheduleSlot)
            .filter(
                ScheduleSlot.task_id == task.id,
                ScheduleSlot.status != SlotStatus.PLANNED.value,
            )
            .update({ScheduleSlot.task_id: None}, synchronize_session=False)
        )
        db.delete(task)
        db.commit()
