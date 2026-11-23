import math
from datetime import date, timedelta
from typing import Dict, List, Any


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
        """
        Возвращает значения биоритмов на указанную дату (в процентах от -100 до +100).
        """
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
        В такие дни биоритм меняет знак.
        """
        days_today = (target_date - birth_date).days
        days_yesterday = days_today - 1

        critical_cycles = []
        cycles = [
            ("Физический", cls.PHYSICAL_PERIOD),
            ("Эмоциональный", cls.EMOTIONAL_PERIOD),
            ("Интеллектуальный", cls.INTELLECTUAL_PERIOD),
        ]

        for name, period in cycles:
            val_prev = cls._calculate_sine(days_yesterday, period)
            val_curr = cls._calculate_sine(days_today, period)

            # Если знак изменился или значение ровно 0 — график пересёк нулевую отметку
            if (val_prev < 0 and val_curr >= 0) or (val_prev > 0 and val_curr <= 0) or val_curr == 0:
                critical_cycles.append(name)

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
    def get_forecast(cls, birth_date: date, start_date: date, days_count: int = 7) -> List[Dict[str, Any]]:
        """Генерация массива данных для отрисовки графиков на фронтенде."""
        forecast = []
        for i in range(days_count):
            current_day = start_date + timedelta(days=i)
            values = cls.get_day_values(birth_date, current_day)
            crit = cls.check_critical_day(birth_date, current_day)
            forecast.append({
                "date": current_day.isoformat(),
                "values": values,
                "is_critical": crit["is_critical"],
            })
        return forecast


# ==========================================
# Тестовый запуск модуля в терминале
# ==========================================
if __name__ == "__main__":
    # Пример пользователя (дата рождения: 1 мая 2006)
    user_birth = date(2006, 5, 1)
    today = date.today()

    print(f"=== РАСЧЁТ БИОРИТМОВ НА {today} ===")
    print(f"Дата рождения: {user_birth}\n")

    values = BiorhythmCalculator.get_day_values(user_birth, today - timedelta(days=1))
    print("\nПоказатели энергии вчера:")
    print(f"  • Физический цикл:       {values['physical']:>6}%")
    print(f"  • Эмоциональный цикл:    {values['emotional']:>6}%")
    print(f"  • Интеллектуальный цикл: {values['intellectual']:>6}%")


    # 1. Текущие значения
    values = BiorhythmCalculator.get_day_values(user_birth, today)
    print("Текущие показатели энергии:")
    print(f"  • Физический цикл:       {values['physical']:>6}%")
    print(f"  • Эмоциональный цикл:    {values['emotional']:>6}%")
    print(f"  • Интеллектуальный цикл: {values['intellectual']:>6}%")

    # 2. Проверка на критический день
    critical_info = BiorhythmCalculator.check_critical_day(user_birth, today)
    print(f"\nСтатус дня: {critical_info['status']}")
    if critical_info["is_critical"]:
        print(f"Затронутые циклы: {', '.join(critical_info['critical_cycles'])}")

    # 3. Прогноз на ближайшие 3 дня
    print("\nПрогноз на 3 дня вперёд:")
    forecast = BiorhythmCalculator.get_forecast(user_birth, today, days_count=3)
    for day_data in forecast:
        val = day_data['values']
        crit_mark = "⚠️ КРИТИЧЕСКИЙ" if day_data['is_critical'] else "OK"
        print(f"  [{day_data['date']}] Физ: {val['physical']}%, Эмо: {val['emotional']}%, Инт: {val['intellectual']}% ({crit_mark})")