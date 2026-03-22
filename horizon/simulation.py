from datetime import datetime, timezone

import numpy as np

from horizon.models import (
    EstimationRequest,
    EstimationResult,
    PercentileEstimate,
    Task,
)


def _compute_ratios(tasks: list[Task]) -> np.ndarray:
    """Return array of actual_days / estimated_days for each task."""
    return np.array([t.actual_days / t.estimated_days for t in tasks])


def _compute_weights(tasks: list[Task], target_sp: float, sigma: float) -> np.ndarray:
    """Gaussian similarity weighting by story points.

    w_i = exp(-0.5 * ((sp_i - target_sp) / sigma)^2), then normalized to sum to 1.
    """
    sp = np.array([t.story_points for t in tasks], dtype=float)
    raw = np.exp(-0.5 * ((sp - target_sp) / sigma) ** 2)
    total = raw.sum()
    if total == 0:
        # Fallback to uniform if all weights collapse to zero
        return np.ones(len(tasks)) / len(tasks)
    return raw / total


def _bootstrap_sample(
    ratios: np.ndarray,
    weights: np.ndarray,
    n_iterations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Weighted bootstrap resampling. Returns sampled ratios of length n_iterations."""
    indices = rng.choice(len(ratios), size=n_iterations, replace=True, p=weights)
    return ratios[indices]


def _extract_percentiles(samples: np.ndarray) -> PercentileEstimate:
    """Extract P10, P50, P90 from a sample array."""
    p10, p50, p90 = np.percentile(samples, [10, 50, 90])
    return PercentileEstimate(p10=float(p10), p50=float(p50), p90=float(p90))


def run_estimation(
    request: EstimationRequest,
    historical_tasks: list[Task],
    iterations: int = 10_000,
    sigma: float = 2.5,
    seed: int | None = None,
) -> EstimationResult:
    """Run Monte Carlo effort estimation via weighted bootstrap resampling.

    Steps:
    1. Compute actual/estimated ratio for each historical task.
    2. Compute Gaussian similarity weights based on story point distance.
    3. Bootstrap-sample ratios, multiply by initial_estimate_days.
    4. Extract P10, P50, P90 percentiles.

    Calendar estimation and reference cases are populated by Tasks 5-7.
    """
    if len(historical_tasks) == 0:
        raise ValueError("Cannot run estimation with no historical tasks")

    rng = np.random.default_rng(seed)

    # Core effort simulation
    ratios = _compute_ratios(historical_tasks)
    weights = _compute_weights(historical_tasks, request.story_points, sigma)
    sampled_ratios = _bootstrap_sample(ratios, weights, iterations, rng)
    effort_samples = sampled_ratios * request.initial_estimate_days

    effort_estimate = _extract_percentiles(effort_samples)

    # Placeholders for calendar estimation and reference cases (Tasks 5-7)
    calendar_estimate = PercentileEstimate(p10=0.0, p50=0.0, p90=0.0)
    calendar_samples: list[float] = []
    reference_cases: list = []

    return EstimationResult(
        request=request,
        team_name="",
        effort_days=effort_estimate,
        calendar_days=calendar_estimate,
        simulation_samples=effort_samples.tolist(),
        calendar_samples=calendar_samples,
        reference_cases=reference_cases,
        dataset_size=len(historical_tasks),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
