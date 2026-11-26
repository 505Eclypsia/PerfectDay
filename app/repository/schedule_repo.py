from datetime import date, time
from typing import List, Optional

from sqlalchemy.orm import Session

from app.model.enums import SlotStatus
from app.model.models import ScheduleSlot


class ScheduleRepository:
    @staticmethod
    def list_by_user_and_date(
        db: Session, user_id: int, target_date: date
    ) -> List[ScheduleSlot]:
        return (
            db.query(ScheduleSlot)
            .filter(ScheduleSlot.user_id == user_id, ScheduleSlot.date == target_date)
            .order_by(ScheduleSlot.start_time.asc(), ScheduleSlot.id.asc())
            .all()
        )

    @staticmethod
    def get_by_id_and_user(
        db: Session, slot_id: int, user_id: int
    ) -> Optional[ScheduleSlot]:
        return (
            db.query(ScheduleSlot)
            .filter(ScheduleSlot.id == slot_id, ScheduleSlot.user_id == user_id)
            .first()
        )

    @staticmethod
    def delete_unfixed_planned(
        db: Session, user_id: int, target_date: date
    ) -> None:
        (
            db.query(ScheduleSlot)
            .filter(
                ScheduleSlot.user_id == user_id,
                ScheduleSlot.date == target_date,
                ScheduleSlot.status == SlotStatus.PLANNED.value,
                ScheduleSlot.is_fixed.is_(False),
            )
            .delete(synchronize_session=False)
        )
        db.commit()

    @staticmethod
    def create_many(db: Session, slots: List[ScheduleSlot]) -> List[ScheduleSlot]:
        db.add_all(slots)
        db.commit()
        for slot in slots:
            db.refresh(slot)
        return slots

    @staticmethod
    def create_one(
        db: Session,
        user_id: int,
        target_date: date,
        start_time: time,
        end_time: time,
        title: str,
        slot_type: str,
        task_id: Optional[int] = None,
        is_fixed: bool = True,
        reason: Optional[str] = None,
        warning: Optional[str] = None,
    ) -> ScheduleSlot:
        slot = ScheduleSlot(
            user_id=user_id,
            task_id=task_id,
            title=title,
            type=slot_type,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            status=SlotStatus.PLANNED.value,
            is_fixed=is_fixed,
            reason=reason,
            warning=warning,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)
        return slot

    @staticmethod
    def save(db: Session, slot: ScheduleSlot) -> ScheduleSlot:
        db.commit()
        db.refresh(slot)
        return slot

    @staticmethod
    def delete(db: Session, slot: ScheduleSlot) -> None:
        db.delete(slot)
        db.commit()
