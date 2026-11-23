"""
Чистый алгоритм укладки задач по слотам дня.
Не знает ни про HTTP, ни про БД, ни про хронотип: получает готовые окна дня
(уже адаптированные под биоритмы) и значения биоритмов.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.config import planner_config as cfg
from app.model.enums import TaskType


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
    start: int                          # минуты от 00:00
    score: float
    reason: str
    warning: Optional[str] = None

    @property
    def end(self) -> int:
        return self.start + self.task.minutes


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def slots_needed(minutes: int) -> int:
    """Сколько слотов занимает задача (округление вверх, минимум один)."""
    return max(1, -(-minutes // cfg.STEP))


def expand_windows(windows: Dict[str, TaskType]) -> List[TaskType]:
    """{"09:00-12:00": TaskType.X, ...} -> тип блока для каждого 30-минутного слота."""
    blocks = [TaskType.REST] * cfg.N_SLOTS
    for key, block_type in windows.items():
        a, b = key.split("-")
        for m in range(_to_min(a), _to_min(b), cfg.STEP):
            blocks[(m - cfg.DAY_START) // cfg.STEP] = block_type
    return blocks


def slot_score(task: Task, block: TaskType, bio: Dict[str, float], critical: bool) -> float:
    base = cfg.FIT.get((task.type, block), 0.0)
    cycle = cfg.CYCLE_OF.get(task.type)
    level = bio[cycle] / 100 if cycle else 0.0           # от -1 до +1
    s = base * (1 + cfg.BIO_WEIGHT * level)
    if critical and task.type in cfg.HARD:
        s *= cfg.CRITICAL_PENALTY
    return s


def task_warning(task: Task, bio: Dict[str, float]) -> Optional[str]:
    """Предупреждение, если тип задачи попал на глубокий спад своего цикла."""
    if task.type == TaskType.INTELLECTUAL and bio["intellectual"] < cfg.INTEL_DROP_THRESHOLD:
        return (f"Интеллект на спаде ({bio['intellectual']:+.1f}%): "
                f"сложную задачу лучше перенести на день с подъёмом.")
    if task.type == TaskType.PHYSICAL and bio["physical"] < cfg.PHYS_DROP_THRESHOLD:
        return f"Физический спад ({bio['physical']:+.1f}%): выберите лёгкую нагрузку."
    return None


def schedule(tasks: List[Task], windows: Dict[str, TaskType], bio: Dict[str, float],
             critical: bool = False) -> Tuple[List[Placement], List[Task]]:
    """Возвращает (размещённые задачи по времени, не поместившиеся задачи)."""
    blocks = expand_windows(windows)
    taken: List[Optional[object]] = [None] * cfg.N_SLOTS    # None / TaskType / "break"
    placed: List[Placement] = []
    unplaced: List[Task] = []

    def hard_run_before(i: int) -> int:
        n = 0
        while i - 1 - n >= 0 and taken[i - 1 - n] in cfg.HARD:
            n += 1
        return n

    # 1. задачи с жёстким временем
    for t in (x for x in tasks if x.fixed_start is not None):
        i = (t.fixed_start - cfg.DAY_START) // cfg.STEP
        need = slots_needed(t.minutes)
        if i < 0 or i + need > cfg.N_SLOTS or any(taken[i:i + need]):
            unplaced.append(t)       # вышла за пределы дня или конфликт
            continue
        for j in range(i, i + need):
            taken[j] = t.type
        placed.append(Placement(t, t.fixed_start, 1.0, "время задано пользователем",
                                task_warning(t, bio)))

    # 2. остальные: приоритет, затем длинные раньше
    flexible = [x for x in tasks if x.fixed_start is None]
    flexible.sort(key=lambda t: (-t.priority, -t.minutes))

    for t in flexible:
        need = slots_needed(t.minutes)
        best_i, best_s = None, 0.0
        for i in range(cfg.N_SLOTS - need + 1):
            if any(taken[i:i + need]):
                continue
            scores = [slot_score(t, blocks[j], bio, critical) for j in range(i, i + need)]
            if min(scores) <= 0:     # хотя бы один слот совсем не подходит по типу
                continue
            s = sum(scores) / need
            if t.type in cfg.HARD and hard_run_before(i) + need > cfg.MAX_HARD_SLOTS:
                s *= cfg.OVERLOAD_PENALTY
            if s > best_s:
                best_i, best_s = i, s

        if best_i is None:
            unplaced.append(t)
            continue

        for j in range(best_i, best_i + need):
            taken[j] = t.type
        end = best_i + need
        if t.minutes >= cfg.BREAK_AFTER_MIN and end < cfg.N_SLOTS and taken[end] is None:
            taken[end] = "break"     # перерыв после долгой задачи

        cycle = cfg.CYCLE_OF.get(t.type)
        level = f"{bio[cycle]:+.1f}%" if cycle else "без цикла"
        block_names = "/".join(dict.fromkeys(b.value for b in blocks[best_i:end]))
        reason = (f"блок дня: {block_names}, цикл ({cycle or '-'}): {level}"
                  + (", критический день: нагрузка снижена" if critical and t.type in cfg.HARD else ""))
        placed.append(Placement(t, cfg.DAY_START + best_i * cfg.STEP, best_s, reason,
                                task_warning(t, bio)))

    placed.sort(key=lambda p: p.start)
    return placed, unplaced
