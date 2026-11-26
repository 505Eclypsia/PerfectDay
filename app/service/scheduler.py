from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from app.model.enums import Chronotype
from app.service.biorhythm import BiorhythmCalculator
from app.service.chronotype import ChronotypeManager, DayNote
from app.service.planner import OccupiedSlot, Placement, Task, schedule


@dataclass
class DayPlan:
    date: date
    biorhythms: Dict[str, float]
    is_critical: bool
    critical_cycles: List[str]
    status: str
    notes: List[DayNote]
    placements: List[Placement]
    unplaced: List[Task]


def build_day_plan(
    birth_date: date,
    chronotype: Chronotype,
    target_date: date,
    tasks: List[Task],
    occupied: Optional[List[OccupiedSlot]] = None,
) -> DayPlan:
    bio = BiorhythmCalculator.get_day_values(birth_date, target_date)
    crit = BiorhythmCalculator.check_critical_day(birth_date, target_date)
    adapted = ChronotypeManager.adapt_day_with_biorhythms(
        chronotype, bio, crit["is_critical"]
    )
    placements, unplaced = schedule(
        tasks, adapted.windows, bio, crit["is_critical"], occupied=occupied
    )
    return DayPlan(
        date=target_date,
        biorhythms=bio,
        is_critical=crit["is_critical"],
        critical_cycles=crit["critical_cycles"],
        status=crit["status"],
        notes=adapted.notes,
        placements=placements,
        unplaced=unplaced,
    )
