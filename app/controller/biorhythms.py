from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.controller.deps import get_current_user
from app.model.enums import Chronotype
from app.model.models import User
from app.schema.biorhythm import (
    BiorhythmDayOut,
    BiorhythmValuesOut,
    DayNoteOut,
    ForecastPointOut,
)
from app.schema.common import ErrorOut
from app.service.biorhythm import BiorhythmCalculator
from app.service.chronotype import ChronotypeManager

router = APIRouter(prefix="/biorhythms", tags=["Биоритмы"])


def _build_biorhythm_day(user: User, target_date: date) -> BiorhythmDayOut:
    try:
        values = BiorhythmCalculator.get_day_values(user.birth_date, target_date)
        crit = BiorhythmCalculator.check_critical_day(user.birth_date, target_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    adapted = ChronotypeManager.adapt_day_with_biorhythms(
        Chronotype(user.chronotype), values, crit["is_critical"]
    )
    return BiorhythmDayOut(
        date=target_date,
        values=BiorhythmValuesOut(**values),
        is_critical=crit["is_critical"],
        critical_cycles=crit["critical_cycles"],
        status=crit["status"],
        notes=[DayNoteOut(window=n.window, text=n.text) for n in adapted.notes],
    )


@router.get(
    "",
    response_model=BiorhythmDayOut,
    summary="Биоритмы и рекомендации на выбранный день",
    responses={401: {"model": ErrorOut}},
)
def get_biorhythms(
    date_param: Optional[date] = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_user),
) -> BiorhythmDayOut:
    return _build_biorhythm_day(current_user, date_param or date.today())


@router.get(
    "/today",
    response_model=BiorhythmDayOut,
    summary="Биоритмы и рекомендации на сегодня",
    responses={401: {"model": ErrorOut}},
)
def get_biorhythms_today(
    current_user: User = Depends(get_current_user),
) -> BiorhythmDayOut:
    return _build_biorhythm_day(current_user, date.today())


@router.get(
    "/forecast",
    response_model=List[ForecastPointOut],
    summary="Прогноз биоритмов на 1–31 день вперёд",
    responses={401: {"model": ErrorOut}},
)
def get_forecast(
    start_date: Optional[date] = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    current_user: User = Depends(get_current_user),
) -> List[ForecastPointOut]:
    base_date = start_date or date.today()
    try:
        points = BiorhythmCalculator.get_forecast(
            current_user.birth_date, base_date, days_count=days
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return [
        ForecastPointOut(
            date=date.fromisoformat(p["date"]),
            values=BiorhythmValuesOut(**p["values"]),
            is_critical=p["is_critical"],
            critical_cycles=p["critical_cycles"],
        )
        for p in points
    ]
