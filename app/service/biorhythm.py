import math
from datetime import date, timedelta
from typing import Any, Dict, List


class BiorhythmCalculator:
    PHYSICAL_PERIOD = 23
    EMOTIONAL_PERIOD = 28
    INTELLECTUAL_PERIOD = 33

    @staticmethod
    def _calculate_sine(days_alive: int, period: int) -> float:
        """Расчёт синусоиды биоритма. Возвращает значение от -1.0 до 1.0."""
        val = math.sin(2 * math.pi * days_alive / period)
        return round(val, 3) + 0.0

    @classmethod
    def get_day_values(cls, birth_date: date, target_date: date) -> Dict[str, float]:
        """Возвращает значения биоритмов на указанную дату (в процентах от -100 до +100)."""
        days_alive = (target_date - birth_date).days
        if days_alive < 0:
            raise ValueError("Дата расчёта не может быть раньше даты рождения.")

        return {
            "physical": round(cls._calculate_sine(days_alive, cls.PHYSICAL_PERIOD) * 100, 1),
            "emotional": round(cls._calculate_sine(days_alive, cls.EMOTIONAL_PERIOD) * 100, 1),
            "intellectual": round(cls._calculate_sine(days_alive, cls.INTELLECTUAL_PERIOD) * 100, 1),
        }

    @classmethod
    def check_critical_day(cls, birth_date: date, target_date: date) -> Dict[str, Any]:
        """
        Определяет критические дни (переход синусоиды через 0).
        Возвращает латинские коды циклов (physical, emotional, intellectual).
        """
        days_today = (target_date - birth_date).days
        if days_today < 0:
            raise ValueError("Дата расчёта не может быть раньше даты рождения.")
        days_yesterday = days_today - 1

        critical_cycles: List[str] = []
        cycles = [
            ("physical", cls.PHYSICAL_PERIOD),
            ("emotional", cls.EMOTIONAL_PERIOD),
            ("intellectual", cls.INTELLECTUAL_PERIOD),
        ]

        for code, period in cycles:
            val_prev = cls._calculate_sine(days_yesterday, period)
            val_curr = cls._calculate_sine(days_today, period)

            if (val_prev < 0 and val_curr >= 0) or (val_prev > 0 and val_curr <= 0) or val_curr == 0:
                critical_cycles.append(code)

        count = len(critical_cycles)
        risk_level = "Обычный день"
        if count == 1:
            risk_level = "Одинарный критический день (повышенная уязвимость)"
        elif count == 2:
            risk_level = "Двойной критический день (высокий риск ошибок, снизьте нагрузку!)"
        elif count == 3:
            risk_level = "Тройной критический день (критический спад, максимальный отдых)"

        return {
            "is_critical": count > 0,
            "critical_count": count,
            "critical_cycles": critical_cycles,
            "status": risk_level,
        }

    @classmethod
    def get_forecast(
        cls, birth_date: date, start_date: date, days_count: int = 7
    ) -> List[Dict[str, Any]]:
        """Генерация массива данных для отрисовки графиков на фронтенде."""
        forecast: List[Dict[str, Any]] = []
        for i in range(days_count):
            current_day = start_date + timedelta(days=i)
            values = cls.get_day_values(birth_date, current_day)
            crit = cls.check_critical_day(birth_date, current_day)
            forecast.append(
                {
                    "date": current_day.isoformat(),
                    "values": values,
                    "is_critical": crit["is_critical"],
                    "critical_cycles": crit["critical_cycles"],
                }
            )
        return forecast