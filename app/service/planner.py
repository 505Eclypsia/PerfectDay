from enum import Enum
from typing import Dict, List, Any

from app.service.biorhythm import BiorhythmCalculator


class Chronotype(str, Enum):
    LARK = "lark"
    OWL = "owl"
    PIGEON = "pigeon"


class TaskType(str, Enum):
    INTELLECTUAL = "intellectual"
    PHYSICAL = "physical"
    CREATIVE = "creative"
    ROUTINE = "routine"
    REST = "rest"


class Planner:
    """
    Управляет базовыми суточными шаблонами активности (с 08:00 до 22:00)
    в зависимости от хронотипа пользователя.
    """

    _PROFILES: Dict[Chronotype, Dict[str, TaskType]] = {
        Chronotype.LARK: {
            "08:00-09:00": TaskType.ROUTINE,
            "09:00-12:00": TaskType.INTELLECTUAL,
            "12:00-13:00": TaskType.REST,
            "13:00-15:00": TaskType.CREATIVE,
            "15:00-17:00": TaskType.PHYSICAL,
            "17:00-19:00": TaskType.ROUTINE,
            "19:00-22:00": TaskType.REST,
        },

        Chronotype.OWL: {
            "08:00-11:00": TaskType.ROUTINE,
            "11:00-13:00": TaskType.CREATIVE,
            "13:00-14:00": TaskType.REST,
            "14:00-16:00": TaskType.ROUTINE,
            "16:00-18:00": TaskType.PHYSICAL,
            "18:00-21:00": TaskType.INTELLECTUAL,
            "21:00-22:00": TaskType.REST,
        },

        Chronotype.PIGEON: {
            "08:00-10:00": TaskType.ROUTINE,
            "10:00-12:30": TaskType.INTELLECTUAL,
            "12:30-13:30": TaskType.REST,
            "13:30-15:30": TaskType.CREATIVE,
            "15:30-17:30": TaskType.PHYSICAL,
            "17:30-19:30": TaskType.ROUTINE,
            "19:30-22:00": TaskType.REST,
        },
    }

from dataclasses import dataclass
from typing import List, Optional, Tuple


STEP = 30
DAY_START, DAY_END = 8 * 60, 22 * 60
N_SLOTS = (DAY_END - DAY_START) // STEP

HARD = {TaskType.INTELLECTUAL}
MAX_HARD_SLOTS = 6
BREAK_AFTER_MIN = 90
CRITICAL_PENALTY = 0.6

FIT = {
    (TaskType.INTELLECTUAL, TaskType.INTELLECTUAL): 1.0,
    (TaskType.INTELLECTUAL, TaskType.CREATIVE): 0.5,
    (TaskType.PHYSICAL, TaskType.PHYSICAL): 1.0,
    (TaskType.CREATIVE, TaskType.CREATIVE): 1.0,
    (TaskType.CREATIVE, TaskType.INTELLECTUAL): 0.4,
    (TaskType.ROUTINE, TaskType.ROUTINE): 1.0,
    (TaskType.ROUTINE, TaskType.REST): 0.2,
    (TaskType.REST, TaskType.REST): 1.0,
}
CYCLE_OF = {
    TaskType.INTELLECTUAL: "intellectual",
    TaskType.PHYSICAL: "physical",
    TaskType.CREATIVE: "emotional",
}


@dataclass
class Task:
    title: str
    type: TaskType
    minutes: int
    priority: int = 1
    fixed_start: Optional[int] = None   # минуты от 00:00, если время задано жёстко


@dataclass
class Placement:
    task: Task
    start: int          # минуты от 00:00
    score: float
    reason: str


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def expand_profile(profile: dict) -> List[TaskType]:
    """{"09:00-12:00": TaskType.X, ...} -> тип блока для каждого 30-минутного слота."""
    blocks = [TaskType.REST] * N_SLOTS
    for key, block_type in profile.items():
        a, b = key.split("-")
        for m in range(_to_min(a), _to_min(b), STEP):
            blocks[(m - DAY_START) // STEP] = block_type
    return blocks


def slot_score(task: Task, block: TaskType, bio: dict, critical: bool) -> float:
    base = FIT.get((task.type, block), 0.0)
    cycle = CYCLE_OF.get(task.type)
    level = bio[cycle] / 100 if cycle else 0.0           # от -1 до +1
    s = base * (1 + 0.5 * level)
    if critical and task.type in HARD:
        s *= CRITICAL_PENALTY
    return s


def schedule(tasks: List[Task], profile: dict, bio: dict,
             critical: bool = False) -> Tuple[List[Placement], List[Task]]:
    blocks = expand_profile(profile)
    taken: List[Optional[object]] = [None] * N_SLOTS     # None / TaskType / "break"
    placed: List[Placement] = []
    unplaced: List[Task] = []

    def hard_run_before(i: int) -> int:
        n = 0
        while i - 1 - n >= 0 and taken[i - 1 - n] in HARD:
            n += 1
        return n

    # 1. задачи с жёстким временем
    for t in (x for x in tasks if x.fixed_start is not None):
        i = (t.fixed_start - DAY_START) // STEP
        need = t.minutes // STEP
        if i < 0 or i + need > N_SLOTS or any(taken[i:i + need]):
            unplaced.append(t)       # вышла за день или конфликт
            continue
        for j in range(i, i + need):
            taken[j] = t.type
        placed.append(Placement(t, t.fixed_start, 1.0, "время задано пользователем"))

    # 2. остальные: приоритет, затем длинные раньше
    flexible = [x for x in tasks if x.fixed_start is None]
    flexible.sort(key=lambda t: (-t.priority, -t.minutes))

    for t in flexible:
        need = max(1, t.minutes // STEP)
        best_i, best_s = None, 0.0
        for i in range(N_SLOTS - need + 1):
            if any(taken[i:i + need]):
                continue
            s = sum(slot_score(t, blocks[j], bio, critical)
                    for j in range(i, i + need)) / need
            if t.type in HARD and hard_run_before(i) + need > MAX_HARD_SLOTS:
                s *= 0.5             # штраф за перегрузку
            if s > best_s:
                best_i, best_s = i, s

        if best_i is None:
            unplaced.append(t)
            continue

        for j in range(best_i, best_i + need):
            taken[j] = t.type
        end = best_i + need
        if t.minutes >= BREAK_AFTER_MIN and end < N_SLOTS and taken[end] is None:
            taken[end] = "break"     # перерыв после долгой задачи

        cycle = CYCLE_OF.get(t.type)
        level = f"{bio[cycle]:+.0f}%" if cycle else "без цикла"
        reason = (f"блок хронотипа: {blocks[best_i].value}, "
                  f"цикл ({cycle or '-'}): {level}"
                  + (", критический день: нагрузка снижена" if critical and t.type in HARD else ""))
        placed.append(Placement(t, DAY_START + best_i * STEP, best_s, reason))

    placed.sort(key=lambda p: p.start)
    return placed, unplaced


def fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


if __name__ == "__main__":
    from datetime import date
    birth, today = date(2006, 5, 1), date.today()
    bio = BiorhythmCalculator.get_day_values(birth, today)
    crit = BiorhythmCalculator.check_critical_day(birth, today)["is_critical"]

    tasks = [
        Task("Написать отчёт", TaskType.INTELLECTUAL, 120, priority=3),
        Task("Тренировка", TaskType.PHYSICAL, 60, priority=2),
        Task("Ответить на письма", TaskType.ROUTINE, 30),
        Task("Созвон с командой", TaskType.CREATIVE, 120, fixed_start=14 * 60),
        Task("Выгулять собаку", TaskType.ROUTINE, 15)
    ]
    print("Все задания на сегодня:")
    for t in tasks:
        print(f'Задание: {t.title}, тип задания: {t.type}, Время на выполнение (мин): {t.minutes}, Приоритет: {t.priority}, фиксированный старт (минуты с 0:00): {t.fixed_start}')
    print("\n")
    result, left = schedule(tasks, Planner._PROFILES[Chronotype.LARK], bio, crit)
    for p in result:
        print(f"{fmt(p.start)}-{fmt(p.start + p.task.minutes)}  {p.task.title}  ({p.reason})")
    for t in left:
        print(f"НЕ ПОМЕСТИЛОСЬ: {t.title}")