import pytest

from horizon.models import EstimationRequest, Task
from horizon.reference_finder import find_reference_cases


def make_task(id: str = "T-1", story_points: int | float = 5) -> Task:
    return Task(
        id=id,
        name=f"Task {id}",
        story_points=story_points,
        estimated_days=3.0,
        actual_days=4.0,
        calendar_days=6,
        completed_date="2024-06-01",
    )


def make_request(story_points: int | float = 5) -> EstimationRequest:
    return EstimationRequest(
        task_name="New task",
        story_points=story_points,
        initial_estimate_days=3.0,
    )


def make_diverse_tasks() -> list[Task]:
    return [
        make_task("T-1", story_points=2),
        make_task("T-2", story_points=3),
        make_task("T-3", story_points=5),
        make_task("T-4", story_points=5),
        make_task("T-5", story_points=8),
        make_task("T-6", story_points=13),
    ]


class TestFindReferenceCases:
    def test_exact_match_gets_score_one(self):
        tasks = make_diverse_tasks()
        refs = find_reference_cases(make_request(story_points=5), tasks)
        assert refs[0].similarity_score == pytest.approx(1.0)

    def test_sorted_descending_by_score(self):
        tasks = make_diverse_tasks()
        refs = find_reference_cases(make_request(story_points=5), tasks)
        scores = [r.similarity_score for r in refs]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_limits_results(self):
        tasks = make_diverse_tasks()
        refs = find_reference_cases(make_request(story_points=5), tasks, top_n=3)
        assert len(refs) == 3

    def test_fewer_tasks_than_top_n_returns_all(self):
        tasks = [make_task("T-1", story_points=5), make_task("T-2", story_points=8)]
        refs = find_reference_cases(make_request(story_points=5), tasks, top_n=10)
        assert len(refs) == 2

    def test_empty_tasks_returns_empty(self):
        refs = find_reference_cases(make_request(), [])
        assert refs == []

    def test_distant_task_gets_low_score(self):
        tasks = make_diverse_tasks()
        refs = find_reference_cases(make_request(story_points=2), tasks, top_n=10)
        # The task with sp=13 should have a very low score relative to sp=2
        sp13 = [r for r in refs if r.task.story_points == 13][0]
        sp2 = [r for r in refs if r.task.story_points == 2][0]
        assert sp13.similarity_score < sp2.similarity_score
        assert sp13.similarity_score < 0.05

    def test_all_scores_between_zero_and_one(self):
        tasks = make_diverse_tasks()
        refs = find_reference_cases(make_request(story_points=5), tasks, top_n=10)
        for r in refs:
            assert 0.0 <= r.similarity_score <= 1.0

    def test_highest_score_is_one(self):
        """The best match is always normalized to 1.0."""
        tasks = make_diverse_tasks()
        refs = find_reference_cases(make_request(story_points=13), tasks, top_n=10)
        assert refs[0].similarity_score == pytest.approx(1.0)
        assert refs[0].task.story_points == 13

    def test_single_task(self):
        tasks = [make_task("T-1", story_points=8)]
        refs = find_reference_cases(make_request(story_points=3), tasks, top_n=5)
        assert len(refs) == 1
        assert refs[0].similarity_score == pytest.approx(1.0)
