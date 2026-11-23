"""
Оркестратор: соединяет биоритмы, хронотип с правилом адаптации и планировщик.
Именно эту функцию будет вызывать controller (POST /schedule/generate).
"""
from dataclasses import dataclass
from datetime import date
from typing import Dict, List

from app.model.enums import Chronotype, TaskType
from app.service.biorhythm import BiorhythmCalculator
from app.service.chronotype import ChronotypeManager, DayNote
from app.service.planner import Placement, Task, fmt, schedule


@dataclass
class DayPlan:
    date: date
    biorhythms: Dict[str, float]
    is_critical: bool
    status: str
    notes: List[DayNote]
    placements: List[Placement]
    unplaced: List[Task]


def build_day_plan(birth_date: date, chronotype: Chronotype, target_date: date,
                   tasks: List[Task]) -> DayPlan:
    bio = BiorhythmCalculator.get_day_values(birth_date, target_date)
    crit = BiorhythmCalculator.check_critical_day(birth_date, target_date)
    adapted = ChronotypeManager.adapt_day_with_biorhythms(chronotype, bio, crit["is_critical"])
    placements, unplaced = schedule(tasks, adapted.windows, bio, crit["is_critical"])
    return DayPlan(target_date, bio, crit["is_critical"], crit["status"],
                   adapted.notes, placements, unplaced)


if __name__ == "__main__":
    birth, today = date(2006, 5, 1), date.today()
    tasks = [
        Task("Написать отчёт", TaskType.INTELLECTUAL, 120, priority=3),
        Task("Тренировка", TaskType.PHYSICAL, 60, priority=2),
        Task("Ответить на письма", TaskType.ROUTINE, 30),
        Task("Созвон с командой", TaskType.CREATIVE, 120, fixed_start=14 * 60),
        Task("Выгулять собаку", TaskType.ROUTINE, 15),
    ]
    for chrono in (Chronotype.LARK, Chronotype.OWL):
        plan = build_day_plan(birth, chrono, today, tasks)
        print(f"=== {plan.date}, {chrono.value}: {plan.biorhythms} | {plan.status} ===")
        for n in plan.notes:
            print(f"  * {n.window + ': ' if n.window else ''}{n.text}")
        for p in plan.placements:
            print(f"  {fmt(p.start)}-{fmt(p.end)}  {p.task.title}  ({p.reason})")
            if p.warning:
                print(f"      ! {p.warning}")
        for t in plan.unplaced:
            print(f"  НЕ ПОМЕСТИЛОСЬ: {t.title}")
        print()
