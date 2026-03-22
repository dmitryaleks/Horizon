"""Shared Monte Carlo utility functions used by simulation and calendar estimator."""

import numpy as np

from horizon.models import PercentileEstimate, Task


def compute_ratios(tasks: list[Task]) -> np.ndarray:
    """Return array of actual_days / estimated_days for each task."""
    return np.array([t.actual_days / t.estimated_days for t in tasks])


def compute_weights(tasks: list[Task], target_sp: float, sigma: float) -> np.ndarray:
    """Gaussian similarity weighting by story points.

    w_i = exp(-0.5 * ((sp_i - target_sp) / sigma)^2), then normalized to sum to 1.
    """
    sp = np.array([t.story_points for t in tasks], dtype=float)
    raw = np.exp(-0.5 * ((sp - target_sp) / sigma) ** 2)
    total = raw.sum()
    if total == 0:
        return np.ones(len(tasks)) / len(tasks)
    return raw / total


def bootstrap_sample(
    ratios: np.ndarray,
    weights: np.ndarray,
    n_iterations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Weighted bootstrap resampling. Returns sampled ratios of length n_iterations."""
    indices = rng.choice(len(ratios), size=n_iterations, replace=True, p=weights)
    return ratios[indices]


def extract_percentiles(samples: np.ndarray) -> PercentileEstimate:
    """Extract P10, P50, P90 from a sample array."""
    p10, p50, p90 = np.percentile(samples, [10, 50, 90])
    return PercentileEstimate(p10=float(p10), p50=float(p50), p90=float(p90))
