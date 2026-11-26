from datetime import date, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controller.deps import get_current_user
from app.model.enums import Chronotype, SlotStatus, TaskStatus, TaskType
from app.model.models import ScheduleSlot, User
from app.repository.schedule_repo import ScheduleRepository
from app.repository.task_repo import TaskRepository
from app.schema.biorhythm import BiorhythmValuesOut
from app.schema.common import ErrorOut
from app.schema.schedule import (
    DayPlanOut,
    ScheduleGenerateIn,
    SlotCreateIn,
    SlotOut,
    SlotUpdateIn,
    UnplacedTaskOut,
)
from app.service.biorhythm import BiorhythmCalculator
from app.service.planner import OccupiedSlot, Task as PlannerTask, fmt, task_warning
from app.service.scheduler import build_day_plan

router = APIRouter(prefix="/schedule", tags=["Расписание"])


def _time_to_min(t: time) -> int:
    return t.hour * 60 + t.minute


def _str_to_time(hhmm: str) -> time:
    h, m = map(int, hhmm.split(":"))
    return time(hour=h, minute=m)


def _min_to_time(minutes: int) -> time:
    return time(hour=minutes // 60, minute=minutes % 60)


def _slot_to_out(slot: ScheduleSlot) -> SlotOut:
    return SlotOut(
        id=slot.id,
        task_id=slot.task_id,
        title=slot.title,
        type=TaskType(slot.type),
        start_time=slot.start_time.strftime("%H:%M"),
        end_time=slot.end_time.strftime("%H:%M"),
        status=SlotStatus(slot.status),
        is_fixed=slot.is_fixed,
        reason=slot.reason,
        warning=slot.warning,
    )


def _build_day_plan_out(
    db: Session,
    user: User,
    target_date: date,
    unplaced: Optional[List[UnplacedTaskOut]] = None,
) -> DayPlanOut:
    try:
        bio = BiorhythmCalculator.get_day_values(user.birth_date, target_date)
        crit = BiorhythmCalculator.check_critical_day(user.birth_date, target_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    slots = ScheduleRepository.list_by_user_and_date(db, user.id, target_date)
    return DayPlanOut(
        date=target_date,
        biorhythms=BiorhythmValuesOut(**bio),
        is_critical=crit["is_critical"],
        critical_cycles=crit["critical_cycles"],
        status=crit["status"],
        slots=[_slot_to_out(s) for s in slots],
        unplaced=unplaced or [],
    )


def _regenerate_day(db: Session, user: User, target_date: date) -> DayPlanOut:
    ScheduleRepository.delete_unfixed_planned(db, user.id, target_date)
    preserved = ScheduleRepository.list_by_user_and_date(db, user.id, target_date)

    preserved_task_ids = {s.task_id for s in preserved if s.task_id is not None}
    occupied = [
        OccupiedSlot(
            start=_time_to_min(s.start_time),
            end=_time_to_min(s.end_time),
            type=TaskType(s.type),
        )
        for s in preserved
    ]

    active_tasks = TaskRepository.list_active_for_date(
        db, user.id, target_date.weekday()
    )
    planner_tasks = [
        PlannerTask(
            task_id=t.id,
            title=t.title,
            type=TaskType(t.type),
            minutes=t.duration_minutes,
            priority=t.priority,
        )
        for t in active_tasks
        if t.id not in preserved_task_ids
    ]

    try:
        plan = build_day_plan(
            birth_date=user.birth_date,
            chronotype=Chronotype(user.chronotype),
            target_date=target_date,
            tasks=planner_tasks,
            occupied=occupied,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    new_slots = [
        ScheduleSlot(
            user_id=user.id,
            task_id=p.task.task_id,
            title=p.task.title,
            type=p.task.type.value,
            date=target_date,
            start_time=_str_to_time(fmt(p.start)),
            end_time=_str_to_time(fmt(p.end)),
            status=SlotStatus.PLANNED.value,
            is_fixed=False,
            reason=p.reason,
            warning=p.warning,
        )
        for p in plan.placements
    ]
    if new_slots:
        ScheduleRepository.create_many(db, new_slots)

    unplaced_out = [
        UnplacedTaskOut(id=t.task_id, title=t.title) for t in plan.unplaced
    ]
    return _build_day_plan_out(db, user, target_date, unplaced=unplaced_out)


def _check_overlap(
    slots: List[ScheduleSlot],
    start_min: int,
    end_min: int,
    exclude_slot_id: Optional[int] = None,
) -> None:
    for s in slots:
        if exclude_slot_id is not None and s.id == exclude_slot_id:
            continue
        s_start = _time_to_min(s.start_time)
        s_end = _time_to_min(s.end_time)
        if start_min < s_end and end_min > s_start:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Пересечение со слотом «{s.title}» ({s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}).",
            )


@router.post(
    "/generate",
    response_model=DayPlanOut,
    summary="Сгенерировать (или пересчитать) расписание на дату",
    responses={401: {"model": ErrorOut}},
)
def generate_schedule(
    payload: ScheduleGenerateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DayPlanOut:
    return _regenerate_day(db, current_user, payload.date)


@router.get(
    "",
    response_model=DayPlanOut,
    summary="Получить сохранённое расписание на дату",
    responses={401: {"model": ErrorOut}},
)
def get_schedule(
    date_param: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DayPlanOut:
    return _build_day_plan_out(db, current_user, date_param)


@router.post(
    "/slots",
    response_model=DayPlanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать системный слот вручную (Обед, Отдых и т.п.)",
    responses={401: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def create_manual_slot(
    payload: SlotCreateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DayPlanOut:
    start_t = _str_to_time(payload.start_time)
    end_t = _str_to_time(payload.end_time)
    start_min = _time_to_min(start_t)
    end_min = _time_to_min(end_t)
    if start_min >= end_min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Время начала должно быть раньше времени окончания.",
        )

    existing = ScheduleRepository.list_by_user_and_date(db, current_user.id, payload.date)
    _check_overlap(existing, start_min, end_min)

    ScheduleRepository.create_one(
        db=db,
        user_id=current_user.id,
        target_date=payload.date,
        start_time=start_t,
        end_time=end_t,
        title=payload.title.strip(),
        slot_type=payload.type.value,
        task_id=None,
        is_fixed=True,
        reason="создано пользователем вручную",
        warning=None,
    )
    return _build_day_plan_out(db, current_user, payload.date)


@router.patch(
    "/slots/{slot_id}",
    response_model=DayPlanOut,
    summary="Перенести слот или отметить выполнение (done / missed)",
    responses={
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
        409: {"model": ErrorOut},
    },
)
def update_slot(
    slot_id: int,
    payload: SlotUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DayPlanOut:
    slot = ScheduleRepository.get_by_id_and_user(db, slot_id, current_user.id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Слот расписания не найден.",
        )

    moved = payload.start_time is not None or payload.end_time is not None
    if moved:
        old_duration = _time_to_min(slot.end_time) - _time_to_min(slot.start_time)
        new_start_min = (
            _time_to_min(_str_to_time(payload.start_time))
            if payload.start_time is not None
            else _time_to_min(slot.start_time)
        )
        new_end_min = (
            _time_to_min(_str_to_time(payload.end_time))
            if payload.end_time is not None
            else new_start_min + old_duration
        )
        if new_start_min < 8 * 60 or new_end_min > 22 * 60 or new_start_min >= new_end_min:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Границы слота должны находиться в пределах 08:00–22:00.",
            )

        day_slots = ScheduleRepository.list_by_user_and_date(
            db, current_user.id, slot.date
        )
        _check_overlap(day_slots, new_start_min, new_end_min, exclude_slot_id=slot.id)

        bio = BiorhythmCalculator.get_day_values(current_user.birth_date, slot.date)
        slot.start_time = _min_to_time(new_start_min)
        slot.end_time = _min_to_time(new_end_min)
        slot.is_fixed = True
        slot.reason = "перенесено пользователем"
        slot.warning = task_warning(
            PlannerTask(
                title=slot.title,
                type=TaskType(slot.type),
                minutes=new_end_min - new_start_min,
            ),
            bio,
        )

    if payload.status is not None:
        slot.status = payload.status.value
        if payload.status == SlotStatus.DONE and slot.task_id is not None:
            task = TaskRepository.get_by_id_and_user(db, slot.task_id, current_user.id)
            if task is not None and task.status != TaskStatus.ON_REPEAT.value:
                TaskRepository.update(db, task, {"status": TaskStatus.DONE.value})

    ScheduleRepository.save(db, slot)

    if moved:
        return _regenerate_day(db, current_user, slot.date)
    return _build_day_plan_out(db, current_user, slot.date)


@router.delete(
    "/slots/{slot_id}",
    response_model=DayPlanOut,
    summary="Удалить слот расписания",
    responses={401: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
def delete_slot(
    slot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DayPlanOut:
    slot = ScheduleRepository.get_by_id_and_user(db, slot_id, current_user.id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Слот расписания не найден.",
        )
    target_date = slot.date
    ScheduleRepository.delete(db, slot)
    return _build_day_plan_out(db, current_user, target_date)
