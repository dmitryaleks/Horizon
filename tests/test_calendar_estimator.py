from datetime import date, timedelta

import numpy as np
import pytest

from horizon.models import Task
from horizon.calendar_estimator import _compute_calendar_ratios, estimate_calendar_days


def make_task(
    id: str = "T-1",
    story_points: int | float = 5,
    estimated_days: float = 3.0,
    actual_days: float = 4.0,
    calendar_days: int = 6,
) -> Task:
    completed = date(2024, 6, 1)
    started = completed - timedelta(days=calendar_days)
    return Task(
        id=id,
        name=f"Task {id}",
        story_points=story_points,
        estimated_days=estimated_days,
        actual_days=actual_days,
        started_date=started,
        completed_date=completed,
    )


def make_diverse_tasks() -> list[Task]:
    return [
        make_task("T-1", story_points=2, actual_days=1.2, calendar_days=2),
        make_task("T-2", story_points=3, actual_days=2.0, calendar_days=3),
        make_task("T-3", story_points=5, actual_days=4.5, calendar_days=7),
        make_task("T-4", story_points=5, actual_days=5.0, calendar_days=8),
        make_task("T-5", story_points=8, actual_days=7.0, calendar_days=10),
        make_task("T-6", story_points=8, actual_days=9.0, calendar_days=14),
        make_task("T-7", story_points=13, actual_days=12.0, calendar_days=18),
        make_task("T-8", story_points=3, actual_days=2.5, calendar_days=4),
        make_task("T-9", story_points=5, actual_days=3.0, calendar_days=5),
        make_task("T-10", story_points=2, actual_days=0.8, calendar_days=2),
    ]


# --- _compute_calendar_ratios ---

class TestComputeCalendarRatios:
    def test_basic(self):
        tasks = [
            make_task(actual_days=4.0, calendar_days=6),   # ratio = 1.5
            make_task(id="T-2", actual_days=5.0, calendar_days=10),  # ratio = 2.0
        ]
        ratios = _compute_calendar_ratios(tasks)
        np.testing.assert_array_almost_equal(ratios, [1.5, 2.0])

    def test_ratio_equals_one(self):
        tasks = [make_task(actual_days=3.0, calendar_days=3)]
        ratios = _compute_calendar_ratios(tasks)
        assert ratios[0] == pytest.approx(1.0)


# --- estimate_calendar_days ---

class TestEstimateCalendarDays:
    def test_deterministic_with_seed(self):
        tasks = make_diverse_tasks()
        effort = np.full(10000, 5.0)
        pe1, s1 = estimate_calendar_days(effort, tasks, target_story_points=5, rng=np.random.default_rng(42))
        pe2, s2 = estimate_calendar_days(effort, tasks, target_story_points=5, rng=np.random.default_rng(42))
        assert pe1.p50 == pe2.p50
        assert s1 == s2

    def test_p10_lt_p50_lt_p90(self):
        tasks = make_diverse_tasks()
        effort = np.random.default_rng(1).lognormal(mean=1.5, sigma=0.3, size=10000)
        pe, _ = estimate_calendar_days(effort, tasks, target_story_points=5, rng=np.random.default_rng(42))
        assert pe.p10 < pe.p50 < pe.p90

    def test_sample_count_matches_input(self):
        tasks = make_diverse_tasks()
        effort = np.full(7500, 4.0)
        _, samples = estimate_calendar_days(effort, tasks, target_story_points=5, rng=np.random.default_rng(42))
        assert len(samples) == 7500

    def test_calendar_ge_effort_when_ratio_ge_one(self):
        """When all historical calendar/actual ratios >= 1, calendar samples >= effort samples."""
        tasks = [
            make_task("T-1", actual_days=2.0, calendar_days=3),  # ratio 1.5
            make_task("T-2", actual_days=4.0, calendar_days=6),  # ratio 1.5
            make_task("T-3", actual_days=3.0, calendar_days=5),  # ratio ~1.67
        ]
        effort = np.full(5000, 4.0)
        _, samples = estimate_calendar_days(effort, tasks, target_story_points=5, rng=np.random.default_rng(42))
        assert all(s >= 4.0 - 1e-9 for s in samples)

    def test_single_task_converges(self):
        """With one task, all calendar samples = effort * (calendar_days / actual_days)."""
        task = make_task(actual_days=4.0, calendar_days=6)  # ratio = 1.5
        effort = np.full(1000, 10.0)
        pe, samples = estimate_calendar_days(effort, [task], target_story_points=5, rng=np.random.default_rng(42))
        expected = 10.0 * 1.5
        assert pe.p10 == pytest.approx(expected)
        assert pe.p50 == pytest.approx(expected)
        assert pe.p90 == pytest.approx(expected)
        assert all(s == pytest.approx(expected) for s in samples)

    def test_returns_list_not_ndarray(self):
        tasks = make_diverse_tasks()
        effort = np.full(100, 5.0)
        _, samples = estimate_calendar_days(effort, tasks, target_story_points=5, rng=np.random.default_rng(42))
        assert isinstance(samples, list)
