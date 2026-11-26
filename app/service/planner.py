"""
Чистый алгоритм укладки задач по слотам дня.
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
    priority: int = 3
    fixed_start: Optional[int] = None   # минуты от 00:00, если время задано жёстко
    task_id: Optional[int] = None


@dataclass
class OccupiedSlot:
    """Уже занятый интервал дня (закреплённый, выполненный, пропущенный или системный слот)."""

    start: int
    end: int
    type: TaskType


@dataclass
class Placement:
    task: Task
    start: int                          # минуты от 00:00
    score: float
    reason: str
    warning: Optional[str] = None

    @property
    def end(self) -> int:
        return self.start + slots_needed(self.task.minutes) * cfg.STEP


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fmt(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def slots_needed(minutes: int) -> int:
    """Сколько 30-минутных слотов занимает задача (округление вверх, минимум один)."""
    return max(1, -(-minutes // cfg.STEP))


def expand_windows(windows: Dict[str, TaskType]) -> List[TaskType]:
    blocks = [TaskType.REST] * cfg.N_SLOTS
    for key, block_type in windows.items():
        a, b = key.split("-")
        for m in range(_to_min(a), _to_min(b), cfg.STEP):
            blocks[(m - cfg.DAY_START) // cfg.STEP] = block_type
    return blocks


def slot_score(task: Task, block: TaskType, bio: Dict[str, float], critical: bool) -> float:
    base = cfg.FIT.get((task.type, block), 0.0)
    cycle = cfg.CYCLE_OF.get(task.type)
    level = bio[cycle] / 100 if cycle else 0.0
    s = base * max(0.1, 1 + cfg.BIO_WEIGHT * level)
    if critical and task.type in cfg.HARD:
        s *= cfg.CRITICAL_PENALTY
    return s


def task_warning(task: Task, bio: Dict[str, float]) -> Optional[str]:
    if task.type == TaskType.INTELLECTUAL and bio["intellectual"] < cfg.INTEL_DROP_THRESHOLD:
        return (
            f"Интеллект на спаде ({bio['intellectual']:+.1f}%): "
            f"сложную задачу лучше перенести на день с подъёмом."
        )
    if task.type == TaskType.PHYSICAL and bio["physical"] < cfg.PHYS_DROP_THRESHOLD:
        return f"Физический спад ({bio['physical']:+.1f}%): выберите лёгкую нагрузку."
    return None


def schedule(
    tasks: List[Task],
    windows: Dict[str, TaskType],
    bio: Dict[str, float],
    critical: bool = False,
    occupied: Optional[List[OccupiedSlot]] = None,
) -> Tuple[List[Placement], List[Task]]:
    """Возвращает (размещённые задачи по времени, не поместившиеся задачи)."""
    blocks = expand_windows(windows)
    taken: List[Optional[object]] = [None] * cfg.N_SLOTS
    placed: List[Placement] = []
    unplaced: List[Task] = []

    if occupied:
        for occ in occupied:
            s_idx = max(0, (occ.start - cfg.DAY_START) // cfg.STEP)
            e_idx = min(cfg.N_SLOTS, -(-(occ.end - cfg.DAY_START) // cfg.STEP))
            for j in range(s_idx, e_idx):
                taken[j] = occ.type
            if (occ.end - occ.start) >= cfg.BREAK_AFTER_MIN and e_idx < cfg.N_SLOTS and taken[e_idx] is None:
                taken[e_idx] = "break"

    def hard_run_total(i: int, need: int) -> int:
        left = 0
        while i - 1 - left >= 0 and taken[i - 1 - left] in cfg.HARD:
            left += 1
        right = 0
        while i + need + right < cfg.N_SLOTS and taken[i + need + right] in cfg.HARD:
            right += 1
        return left + need + right

    # 1. Задачи с жёстким временем
    for t in (x for x in tasks if x.fixed_start is not None):
        if (t.fixed_start - cfg.DAY_START) % cfg.STEP != 0:
            unplaced.append(t)
            continue
        i = (t.fixed_start - cfg.DAY_START) // cfg.STEP
        need = slots_needed(t.minutes)
        if i < 0 or i + need > cfg.N_SLOTS or any(taken[i : i + need]):
            unplaced.append(t)
            continue
        for j in range(i, i + need):
            taken[j] = t.type
        end_idx = i + need
        if t.minutes >= cfg.BREAK_AFTER_MIN and end_idx < cfg.N_SLOTS and taken[end_idx] is None:
            taken[end_idx] = "break"
        placed.append(
            Placement(t, t.fixed_start, 1.0, "время задано пользователем", task_warning(t, bio))
        )

    # 2. Остальные: приоритет (5 -> 1), затем длинные раньше
    flexible = [x for x in tasks if x.fixed_start is None]
    flexible.sort(key=lambda t: (-t.priority, -t.minutes))

    for t in flexible:
        need = slots_needed(t.minutes)
        best_i, best_s = None, 0.0
        for i in range(cfg.N_SLOTS - need + 1):
            if any(taken[i : i + need]):
                continue
            scores = [slot_score(t, blocks[j], bio, critical) for j in range(i, i + need)]
            if min(scores) <= 0:
                continue
            s = sum(scores) / need
            if t.type in cfg.HARD and hard_run_total(i, need) > cfg.MAX_HARD_SLOTS:
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
            taken[end] = "break"

        cycle = cfg.CYCLE_OF.get(t.type)
        level = f"{bio[cycle]:+.1f}%" if cycle else "без цикла"
        block_names = "/".join(dict.fromkeys(b.value for b in blocks[best_i:end]))
        reason = (
            f"блок дня: {block_names}, цикл ({cycle or '-'}): {level}"
            + (", критический день: нагрузка снижена" if critical and t.type in cfg.HARD else "")
        )
        placed.append(
            Placement(
                t,
                cfg.DAY_START + best_i * cfg.STEP,
                best_s,
                reason,
                task_warning(t, bio),
            )
        )

    placed.sort(key=lambda p: p.start)
    return placed, unplaced
