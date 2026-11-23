"""
Настраиваемые допущения планировщика.

Все числа здесь — экспертные коэффициенты прототипа, а не научно обоснованные
величины. Их можно менять, не трогая алгоритм.
"""
from app.model.enums import TaskType

# --- сетка дня ---
STEP = 30                                  # минут в одном слоте
DAY_START, DAY_END = 8 * 60, 22 * 60       # 08:00-22:00, в минутах от 00:00
N_SLOTS = (DAY_END - DAY_START) // STEP

# --- перегрузка ---
HARD = {TaskType.INTELLECTUAL}             # «сложные» типы задач
MAX_HARD_SLOTS = 6                         # не более 3 часов сложной работы подряд
OVERLOAD_PENALTY = 0.5
BREAK_AFTER_MIN = 90                       # после задачи >= 90 мин резервируем перерыв

# --- влияние биоритмов ---
BIO_WEIGHT = 0.5                           # оценка = совпадение * (1 + BIO_WEIGHT * уровень цикла)
CRITICAL_PENALTY = 0.6                     # множитель для сложных задач в критический день

# --- правила адаптации дня (в процентах цикла) ---
INTEL_DROP_THRESHOLD = -50                 # ниже: сложные блоки заменяются рутиной
PHYS_PEAK_THRESHOLD = 50                   # выше: рекомендация интенсивных нагрузок
PHYS_DROP_THRESHOLD = -50                  # ниже: рекомендация лёгкой нагрузки

# --- соответствие «тип задачи / тип блока» ---
FIT = {
    (TaskType.INTELLECTUAL, TaskType.INTELLECTUAL): 1.0,
    (TaskType.INTELLECTUAL, TaskType.CREATIVE): 0.5,
    (TaskType.INTELLECTUAL, TaskType.ROUTINE): 0.2,   # запасной вариант, когда блок понижен адаптацией
    (TaskType.PHYSICAL, TaskType.PHYSICAL): 1.0,
    (TaskType.CREATIVE, TaskType.CREATIVE): 1.0,
    (TaskType.CREATIVE, TaskType.INTELLECTUAL): 0.4,
    (TaskType.ROUTINE, TaskType.ROUTINE): 1.0,
    (TaskType.ROUTINE, TaskType.REST): 0.2,
    (TaskType.REST, TaskType.REST): 1.0,
}

# --- какой биоритм влияет на какой тип задач ---
CYCLE_OF = {
    TaskType.INTELLECTUAL: "intellectual",
    TaskType.PHYSICAL: "physical",
    TaskType.CREATIVE: "emotional",
}
