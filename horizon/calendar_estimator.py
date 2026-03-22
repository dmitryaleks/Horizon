import numpy as np

from horizon.mc_utils import compute_weights, bootstrap_sample, extract_percentiles
from horizon.models import PercentileEstimate, Task


def _compute_calendar_ratios(tasks: list[Task]) -> np.ndarray:
    """Return array of calendar_days / actual_days for each task."""
    return np.array([t.calendar_days / t.actual_days for t in tasks])


def estimate_calendar_days(
    effort_samples: np.ndarray,
    historical_tasks: list[Task],
    target_story_points: float,
    sigma: float = 2.5,
    rng: np.random.Generator | None = None,
) -> tuple[PercentileEstimate, list[float]]:
    """Estimate calendar days from effort samples using weighted bootstrap.

    Uses calendar_days / actual_days ratios from historical data,
    weighted by story point similarity. Each effort sample is multiplied
    by a bootstrapped calendar ratio to produce a calendar-day sample.

    Returns (percentile_estimate, raw_samples).
    """
    if rng is None:
        rng = np.random.default_rng()

    cal_ratios = _compute_calendar_ratios(historical_tasks)
    weights = compute_weights(historical_tasks, target_story_points, sigma)
    sampled_ratios = bootstrap_sample(cal_ratios, weights, len(effort_samples), rng)

    calendar_samples = effort_samples * sampled_ratios
    percentiles = extract_percentiles(calendar_samples)

    return percentiles, calendar_samples.tolist()
