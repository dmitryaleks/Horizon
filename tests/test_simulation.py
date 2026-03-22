from pathlib import Path

import numpy as np
import pytest

from horizon.data_store import load_team_data
from horizon.mc_utils import compute_ratios, compute_weights, bootstrap_sample, extract_percentiles
from horizon.models import EstimationRequest, Task
from horizon.simulation import run_estimation

FIXTURE = Path(__file__).parent / "fixtures" / "sample_team.json"


# --- Helpers ---

def make_task(
    id: str = "T-1",
    story_points: int | float = 5,
    estimated_days: float = 3.0,
    actual_days: float = 4.0,
    calendar_days: int = 6,
) -> Task:
    return Task(
        id=id,
        name=f"Task {id}",
        story_points=story_points,
        estimated_days=estimated_days,
        actual_days=actual_days,
        calendar_days=calendar_days,
        completed_date="2024-06-01",
    )


def make_request(story_points: int | float = 5, estimate: float = 3.0) -> EstimationRequest:
    return EstimationRequest(
        task_name="New task",
        story_points=story_points,
        initial_estimate_days=estimate,
    )


def make_diverse_tasks() -> list[Task]:
    """A set of tasks with varied story points and ratios."""
    return [
        make_task("T-1", story_points=2, estimated_days=1.0, actual_days=1.2, calendar_days=2),
        make_task("T-2", story_points=3, estimated_days=2.0, actual_days=2.0, calendar_days=3),
        make_task("T-3", story_points=5, estimated_days=3.0, actual_days=4.5, calendar_days=7),
        make_task("T-4", story_points=5, estimated_days=4.0, actual_days=5.0, calendar_days=8),
        make_task("T-5", story_points=8, estimated_days=5.0, actual_days=7.0, calendar_days=10),
        make_task("T-6", story_points=8, estimated_days=6.0, actual_days=9.0, calendar_days=14),
        make_task("T-7", story_points=13, estimated_days=8.0, actual_days=12.0, calendar_days=18),
        make_task("T-8", story_points=3, estimated_days=1.5, actual_days=2.5, calendar_days=4),
        make_task("T-9", story_points=5, estimated_days=3.0, actual_days=3.0, calendar_days=5),
        make_task("T-10", story_points=2, estimated_days=1.0, actual_days=0.8, calendar_days=2),
    ]


# --- compute_ratios ---

class TestComputeRatios:
    def test_basic(self):
        tasks = [
            make_task(estimated_days=2.0, actual_days=4.0),
            make_task(id="T-2", estimated_days=5.0, actual_days=5.0),
        ]
        ratios = compute_ratios(tasks)
        np.testing.assert_array_almost_equal(ratios, [2.0, 1.0])

    def test_single_task(self):
        tasks = [make_task(estimated_days=3.0, actual_days=4.5)]
        ratios = compute_ratios(tasks)
        assert ratios[0] == pytest.approx(1.5)


# --- compute_weights ---

class TestComputeWeights:
    def test_exact_match_gets_highest_weight(self):
        tasks = make_diverse_tasks()
        weights = compute_weights(tasks, target_sp=5.0, sigma=2.5)
        # Tasks with sp=5 should have the highest individual weight
        sp_5_indices = [i for i, t in enumerate(tasks) if t.story_points == 5]
        sp_other_indices = [i for i, t in enumerate(tasks) if t.story_points != 5]
        max_other = max(weights[i] for i in sp_other_indices)
        min_sp5 = min(weights[i] for i in sp_5_indices)
        assert min_sp5 >= max_other

    def test_weights_sum_to_one(self):
        tasks = make_diverse_tasks()
        weights = compute_weights(tasks, target_sp=5.0, sigma=2.5)
        assert weights.sum() == pytest.approx(1.0)

    def test_very_large_sigma_gives_near_uniform(self):
        tasks = make_diverse_tasks()
        weights = compute_weights(tasks, target_sp=5.0, sigma=1000.0)
        expected = 1.0 / len(tasks)
        for w in weights:
            assert w == pytest.approx(expected, abs=1e-4)

    def test_very_small_sigma_concentrates_on_closest(self):
        tasks = make_diverse_tasks()
        weights = compute_weights(tasks, target_sp=5.0, sigma=0.01)
        # Only tasks with sp=5 should have non-negligible weight
        for i, t in enumerate(tasks):
            if t.story_points == 5:
                assert weights[i] > 0.01
            else:
                assert weights[i] < 1e-6

    def test_single_task_gets_weight_one(self):
        tasks = [make_task(story_points=5)]
        weights = compute_weights(tasks, target_sp=8.0, sigma=2.5)
        assert weights[0] == pytest.approx(1.0)


# --- bootstrap_sample ---

class TestBootstrapSample:
    def test_output_length(self):
        ratios = np.array([1.0, 1.2, 1.5])
        weights = np.array([0.3, 0.3, 0.4])
        rng = np.random.default_rng(42)
        samples = bootstrap_sample(ratios, weights, 5000, rng)
        assert len(samples) == 5000

    def test_values_come_from_ratios(self):
        ratios = np.array([1.0, 2.0, 3.0])
        weights = np.array([1 / 3, 1 / 3, 1 / 3])
        rng = np.random.default_rng(42)
        samples = bootstrap_sample(ratios, weights, 1000, rng)
        assert set(samples).issubset({1.0, 2.0, 3.0})

    def test_deterministic_with_seed(self):
        ratios = np.array([1.0, 1.5, 2.0])
        weights = np.array([0.2, 0.5, 0.3])
        s1 = bootstrap_sample(ratios, weights, 100, np.random.default_rng(42))
        s2 = bootstrap_sample(ratios, weights, 100, np.random.default_rng(42))
        np.testing.assert_array_equal(s1, s2)


# --- extract_percentiles ---

class TestExtractPercentiles:
    def test_basic(self):
        samples = np.arange(1.0, 101.0)  # 1 to 100
        pe = extract_percentiles(samples)
        assert pe.p10 == pytest.approx(10.9, abs=0.5)
        assert pe.p50 == pytest.approx(50.5, abs=0.5)
        assert pe.p90 == pytest.approx(90.1, abs=0.5)

    def test_ordering(self):
        rng = np.random.default_rng(42)
        samples = rng.lognormal(mean=1.0, sigma=0.5, size=10000)
        pe = extract_percentiles(samples)
        assert pe.p10 < pe.p50 < pe.p90

    def test_constant_values(self):
        samples = np.full(1000, 5.0)
        pe = extract_percentiles(samples)
        assert pe.p10 == pytest.approx(5.0)
        assert pe.p50 == pytest.approx(5.0)
        assert pe.p90 == pytest.approx(5.0)


# --- run_estimation (integration) ---

class TestRunEstimation:
    def test_deterministic_with_seed(self):
        tasks = make_diverse_tasks()
        req = make_request(story_points=5, estimate=3.0)
        r1 = run_estimation(req, tasks, iterations=5000, seed=42)
        r2 = run_estimation(req, tasks, iterations=5000, seed=42)
        assert r1.effort_days.p50 == r2.effort_days.p50
        assert r1.simulation_samples == r2.simulation_samples

    def test_p10_lt_p50_lt_p90(self):
        tasks = make_diverse_tasks()
        req = make_request(story_points=5, estimate=3.0)
        result = run_estimation(req, tasks, iterations=10000, seed=42)
        assert result.effort_days.p10 < result.effort_days.p50 < result.effort_days.p90

    def test_sample_count_matches_iterations(self):
        tasks = make_diverse_tasks()
        req = make_request()
        result = run_estimation(req, tasks, iterations=7500, seed=1)
        assert len(result.simulation_samples) == 7500

    def test_single_task_converges(self):
        """With one historical task, all samples should equal ratio * estimate."""
        task = make_task(estimated_days=2.0, actual_days=3.0)  # ratio = 1.5
        req = make_request(story_points=5, estimate=4.0)
        result = run_estimation(req, [task], iterations=1000, seed=42)
        expected = 4.0 * 1.5  # 6.0
        assert result.effort_days.p10 == pytest.approx(expected)
        assert result.effort_days.p50 == pytest.approx(expected)
        assert result.effort_days.p90 == pytest.approx(expected)

    def test_empty_tasks_raises(self):
        req = make_request()
        with pytest.raises(ValueError, match="no historical tasks"):
            run_estimation(req, [], seed=42)

    def test_dataset_size_recorded(self):
        tasks = make_diverse_tasks()
        req = make_request()
        result = run_estimation(req, tasks, seed=42)
        assert result.dataset_size == len(tasks)

    def test_result_has_timestamp(self):
        tasks = make_diverse_tasks()
        req = make_request()
        result = run_estimation(req, tasks, iterations=100, seed=42)
        assert result.timestamp  # non-empty string

    def test_estimates_scale_with_initial_estimate(self):
        """Doubling the initial estimate should roughly double the outputs."""
        tasks = make_diverse_tasks()
        r1 = run_estimation(make_request(estimate=3.0), tasks, seed=42)
        r2 = run_estimation(make_request(estimate=6.0), tasks, seed=42)
        assert r2.effort_days.p50 == pytest.approx(r1.effort_days.p50 * 2.0, rel=0.01)

    def test_story_point_weighting_affects_result(self):
        """Estimating a 2-SP task vs 13-SP task with the same initial estimate
        should produce different results due to different weighting."""
        tasks = make_diverse_tasks()
        r_small = run_estimation(make_request(story_points=2, estimate=3.0), tasks, seed=42)
        r_large = run_estimation(make_request(story_points=13, estimate=3.0), tasks, seed=42)
        # The diverse tasks have higher ratios for larger SP tasks, so P50 should differ
        assert r_small.effort_days.p50 != pytest.approx(r_large.effort_days.p50, abs=0.01)


# --- Full pipeline integration (Task 7) ---

class TestFullPipelineIntegration:
    def test_all_fields_populated_from_fixture(self):
        """Load real fixture data and verify the full EstimationResult is populated."""
        td = load_team_data(FIXTURE)
        req = make_request(story_points=5, estimate=3.0)
        result = run_estimation(req, td.tasks, team_name=td.team, iterations=10000, seed=42)

        # Team name
        assert result.team_name == "Team Alpha"

        # Effort
        assert result.effort_days.p10 > 0
        assert result.effort_days.p10 < result.effort_days.p50 < result.effort_days.p90
        assert len(result.simulation_samples) == 10000

        # Calendar
        assert result.calendar_days.p10 > 0
        assert result.calendar_days.p10 < result.calendar_days.p50 < result.calendar_days.p90
        assert len(result.calendar_samples) == 10000

        # Calendar >= effort on average (calendar ratios are >= 1 in fixture)
        assert result.calendar_days.p50 >= result.effort_days.p50

        # Reference cases
        assert len(result.reference_cases) == 5
        assert result.reference_cases[0].similarity_score == pytest.approx(1.0)
        scores = [rc.similarity_score for rc in result.reference_cases]
        assert scores == sorted(scores, reverse=True)

        # Metadata
        assert result.dataset_size == 15
        assert result.timestamp

    def test_custom_top_references(self):
        td = load_team_data(FIXTURE)
        req = make_request(story_points=8, estimate=5.0)
        result = run_estimation(req, td.tasks, top_references=3, seed=42)
        assert len(result.reference_cases) == 3

    def test_calendar_samples_are_list(self):
        td = load_team_data(FIXTURE)
        req = make_request()
        result = run_estimation(req, td.tasks, iterations=100, seed=42)
        assert isinstance(result.calendar_samples, list)
