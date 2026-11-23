from datetime import date, time

from app.model.enums import Chronotype, TaskType
from app.schema.schedule import TaskIn
from app.service.chronotype import ChronotypeManager
from app.service.planner import Task, schedule, expand_windows
from app.service.scheduler import build_day_plan

BIO_SPAD = {"physical": 97.9, "emotional": 78.2, "intellectual": -86.6}   # день из отчёта от 09.11
BIO_OK = {"physical": 10.0, "emotional": 10.0, "intellectual": 80.0}


def test_adapt_replaces_intellectual_blocks_on_deep_drop():
    day = ChronotypeManager.adapt_day_with_biorhythms(Chronotype.OWL, BIO_SPAD)
    assert day.windows["18:00-21:00"] == TaskType.ROUTINE
    assert not any(v == TaskType.INTELLECTUAL for v in day.windows.values())
    texts = [n.text for n in day.notes]
    assert any("Интеллект на спаде (-86.6%)" in t for t in texts)
    assert any(n.window == "16:00-18:00" and "Физический пик" in n.text for n in day.notes)


def test_adapt_keeps_windows_when_intellect_ok():
    day = ChronotypeManager.adapt_day_with_biorhythms(Chronotype.LARK, BIO_OK)
    assert day.windows == ChronotypeManager.get_base_day_windows(Chronotype.LARK)


def test_adapt_critical_day_note_and_base_not_mutated():
    ChronotypeManager.adapt_day_with_biorhythms(Chronotype.OWL, BIO_SPAD)
    assert ChronotypeManager.get_base_day_windows(Chronotype.OWL)["18:00-21:00"] == TaskType.INTELLECTUAL
    day = ChronotypeManager.adapt_day_with_biorhythms(Chronotype.OWL, BIO_OK, is_critical=True)
    assert day.notes[0].window is None and "критический" in day.notes[0].text


def test_intellectual_task_still_placed_on_drop_with_warning():
    task = [Task("Отчёт", TaskType.INTELLECTUAL, 120)]
    ok_windows = ChronotypeManager.adapt_day_with_biorhythms(Chronotype.OWL, BIO_OK).windows
    bad_windows = ChronotypeManager.adapt_day_with_biorhythms(Chronotype.OWL, BIO_SPAD).windows
    good, _ = schedule(task, ok_windows, BIO_OK)
    bad, left = schedule(task, bad_windows, BIO_SPAD)
    assert not left and bad[0].warning and "перенести" in bad[0].warning
    assert good[0].warning is None
    assert bad[0].score < good[0].score
    assert good[0].start == 18 * 60            # вечерний блок «совы» в обычный день


def test_short_fixed_tasks_occupy_a_slot():
    tasks = [Task("A", TaskType.ROUTINE, 15, fixed_start=9 * 60),
             Task("B", TaskType.ROUTINE, 15, fixed_start=9 * 60)]
    placed, left = schedule(tasks, ChronotypeManager.get_base_day_windows(Chronotype.LARK), BIO_OK)
    assert len(placed) == 1 and [t.title for t in left] == ["B"]


def test_fixed_conflict_and_out_of_day():
    tasks = [Task("A", TaskType.CREATIVE, 120, fixed_start=14 * 60),
             Task("B", TaskType.CREATIVE, 60, fixed_start=15 * 60),
             Task("C", TaskType.ROUTINE, 60, fixed_start=21 * 60 + 30)]
    placed, left = schedule(tasks, ChronotypeManager.get_base_day_windows(Chronotype.LARK), BIO_OK)
    assert [p.task.title for p in placed] == ["A"]
    assert sorted(t.title for t in left) == ["B", "C"]


def test_no_overlaps_and_inside_day():
    tasks = [Task(f"T{i}", t, m, priority=p) for i, (t, m, p) in enumerate([
        (TaskType.INTELLECTUAL, 120, 3), (TaskType.INTELLECTUAL, 90, 2), (TaskType.PHYSICAL, 60, 2),
        (TaskType.ROUTINE, 30, 1), (TaskType.ROUTINE, 15, 1), (TaskType.CREATIVE, 60, 1)])]
    placed, _ = schedule(tasks, ChronotypeManager.get_base_day_windows(Chronotype.PIGEON), BIO_OK)
    spans = sorted((p.start, p.end) for p in placed)
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:]))
    assert spans[0][0] >= 8 * 60 and max(e for _, e in spans) <= 22 * 60


def test_profiles_cover_whole_day():
    for c in Chronotype:
        blocks = expand_windows(ChronotypeManager.get_base_day_windows(c))
        assert len(blocks) == 28


def test_build_day_plan_end_to_end():
    tasks = [Task("Отчёт", TaskType.INTELLECTUAL, 120, 3), Task("Тренировка", TaskType.PHYSICAL, 60, 2)]
    plan = build_day_plan(date(2006, 5, 1), Chronotype.OWL, date(2026, 11, 23), tasks)
    assert plan.biorhythms["intellectual"] < -50
    assert not plan.unplaced
    assert any(p.warning for p in plan.placements if p.task.type == TaskType.INTELLECTUAL)


def test_schema_validation():
    t = TaskIn(title="x", type="intellectual", duration_minutes=60, fixed_start=time(9, 0))
    assert t.type == TaskType.INTELLECTUAL


def test_task_never_placed_over_incompatible_block():
    windows = ChronotypeManager.adapt_day_with_biorhythms(Chronotype.LARK, BIO_SPAD).windows
    placed, left = schedule([Task("Отчёт", TaskType.INTELLECTUAL, 120),
                             Task("Созвон", TaskType.CREATIVE, 120, fixed_start=14 * 60)],
                            windows, BIO_SPAD)
    report = next(p for p in placed if p.task.title == "Отчёт")
    blocks = expand_windows(windows)
    first = (report.start - 8 * 60) // 30
    assert all(blocks[j] != TaskType.REST for j in range(first, first + 4))
