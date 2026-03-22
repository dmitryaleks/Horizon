from datetime import datetime, timezone

import numpy as np

from horizon.calendar_estimator import estimate_calendar_days
from horizon.mc_utils import compute_ratios, compute_weights, bootstrap_sample, extract_percentiles
from horizon.models import (
    EstimationRequest,
    EstimationResult,
    Task,
)
from horizon.reference_finder import find_reference_cases


def run_estimation(
    request: EstimationRequest,
    historical_tasks: list[Task],
    team_name: str = "",
    iterations: int = 10_000,
    sigma: float = 2.5,
    seed: int | None = None,
    top_references: int = 5,
) -> EstimationResult:
    """Run full Monte Carlo estimation pipeline.

    Steps:
    1. Compute actual/estimated ratio for each historical task.
    2. Compute Gaussian similarity weights based on story point distance.
    3. Bootstrap-sample ratios, multiply by initial_estimate_days.
    4. Extract P10, P50, P90 percentiles for effort.
    5. Estimate calendar days from effort samples.
    6. Find most similar reference cases.
    """
    if len(historical_tasks) == 0:
        raise ValueError("Cannot run estimation with no historical tasks")

    rng = np.random.default_rng(seed)

    # Core effort simulation
    ratios = compute_ratios(historical_tasks)
    weights = compute_weights(historical_tasks, request.story_points, sigma)
    sampled_ratios = bootstrap_sample(ratios, weights, iterations, rng)
    effort_samples = sampled_ratios * request.initial_estimate_days

    effort_estimate = extract_percentiles(effort_samples)

    # Calendar day estimation
    calendar_estimate, calendar_samples = estimate_calendar_days(
        effort_samples, historical_tasks, request.story_points, sigma, rng,
    )

    # Reference cases
    reference_cases = find_reference_cases(request, historical_tasks, top_references, sigma)

    return EstimationResult(
        request=request,
        team_name=team_name,
        effort_days=effort_estimate,
        calendar_days=calendar_estimate,
        simulation_samples=effort_samples.tolist(),
        calendar_samples=calendar_samples,
        reference_cases=reference_cases,
        dataset_size=len(historical_tasks),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
