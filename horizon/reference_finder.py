import numpy as np

from horizon.models import EstimationRequest, ReferenceCase, Task


def find_reference_cases(
    request: EstimationRequest,
    historical_tasks: list[Task],
    top_n: int = 5,
    sigma: float = 2.5,
) -> list[ReferenceCase]:
    """Rank historical tasks by Gaussian similarity on story points.

    Score is normalized so the highest score = 1.0.
    Returns the top N tasks sorted by score descending.
    """
    if not historical_tasks:
        return []

    sp = np.array([t.story_points for t in historical_tasks], dtype=float)
    raw_scores = np.exp(-0.5 * ((sp - request.story_points) / sigma) ** 2)

    max_score = raw_scores.max()
    if max_score == 0:
        normalized = np.zeros_like(raw_scores)
    else:
        normalized = raw_scores / max_score

    # Pair tasks with scores, sort descending
    scored = sorted(
        zip(historical_tasks, normalized.tolist()),
        key=lambda pair: pair[1],
        reverse=True,
    )

    return [
        ReferenceCase(task=task, similarity_score=score)
        for task, score in scored[:top_n]
    ]
