from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.config import planner_config as cfg
from app.model.enums import Chronotype, TaskType

Windows = Dict[str, TaskType]


@dataclass
class DayNote:
    """Пояснение или предупреждение к дню (window=None) либо к конкретному окну."""

    text: str
    window: Optional[str] = None


@dataclass
class AdaptedDay:
    windows: Windows
    notes: List[DayNote] = field(default_factory=list)


class ChronotypeManager:
    """
    Управляет базовыми суточными шаблонами активности (с 08:00 до 22:00)
    в зависимости от хронотипа пользователя.
    """

    _PROFILES: Dict[Chronotype, Windows] = {
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

    @classmethod
    def get_base_day_windows(cls, chronotype: Chronotype) -> Windows:
        return dict(cls._PROFILES[Chronotype(chronotype)])

    @classmethod
    def adapt_day_with_biorhythms(
        cls,
        chronotype: Chronotype,
        biorhythms: Dict[str, float],
        is_critical: bool = False,
    ) -> AdaptedDay:
        windows = cls.get_base_day_windows(chronotype)
        notes: List[DayNote] = []
        intel, phys = biorhythms["intellectual"], biorhythms["physical"]

        if is_critical:
            notes.append(
                DayNote("Внимание: критический день! Нагрузка снижена, избегайте важных решений.")
            )

        for window, block in list(windows.items()):
            if block == TaskType.INTELLECTUAL:
                if intel < cfg.INTEL_DROP_THRESHOLD:
                    windows[window] = TaskType.ROUTINE
                    notes.append(
                        DayNote(
                            f"Интеллект на спаде ({intel:+.1f}%). Интеллектуальный блок переключён в режим лёгкой рутины.",
                            window,
                        )
                    )
                else:
                    notes.append(DayNote("Оптимальное окно по вашему хронотипу.", window))
            elif block == TaskType.PHYSICAL:
                if phys > cfg.PHYS_PEAK_THRESHOLD:
                    notes.append(
                        DayNote(
                            f"Физический пик ({phys:+.1f}%)! Идеальное время для интенсивных нагрузок.",
                            window,
                        )
                    )
                elif phys < cfg.PHYS_DROP_THRESHOLD:
                    notes.append(
                        DayNote(
                            f"Физический спад ({phys:+.1f}%). Замените тяжёлый спорт лёгкой прогулкой.",
                            window,
                        )
                    )

        return AdaptedDay(windows=windows, notes=notes)
