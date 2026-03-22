from datetime import datetime, timezone

import numpy as np

from horizon.calendar_estimator import estimate_calendar_days, _compute_calendar_ratios
from horizon.mc_utils import (
    compute_distribution_stats,
    compute_ratios,
    compute_weights,
    bootstrap_sample,
    extract_percentiles,
)
from horizon.models import (
    EstimationRequest,
    EstimationResult,
    InfluentialTask,
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

    # Extended statistics
    effort_stats = compute_distribution_stats(effort_samples, effort_estimate)
    calendar_stats = compute_distribution_stats(
        np.array(calendar_samples), calendar_estimate,
    )
    prob_exceed = float(np.mean(effort_samples > request.initial_estimate_days))

    cal_ratios = _compute_calendar_ratios(historical_tasks)

    # Influential tasks (top 10 by weight)
    sorted_pairs = sorted(
        zip(historical_tasks, weights.tolist()), key=lambda p: p[1], reverse=True,
    )
    influential = [
        InfluentialTask(task=t, weight=w) for t, w in sorted_pairs[:10]
    ]

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
        effort_stats=effort_stats,
        calendar_stats=calendar_stats,
        prob_exceed_estimate=prob_exceed,
        historical_accuracy_mean=float(ratios.mean()),
        historical_accuracy_stdev=float(ratios.std(ddof=1)) if len(ratios) > 1 else 0.0,
        calendar_overhead_mean=float(cal_ratios.mean()),
        influential_tasks=influential,
    )
