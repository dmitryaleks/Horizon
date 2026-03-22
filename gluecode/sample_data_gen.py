"""Generate synthetic historical task data for testing and demos."""

import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np


FIBONACCI_SP = [1, 2, 3, 5, 8, 13]


def generate_tasks(count: int, team: str, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    start_date = date(2024, 1, 8)  # a Monday
    tasks = []

    for i in range(count):
        sp = rng.choice(FIBONACCI_SP)

        # Estimated days: 0.5-1.5 days per story point
        days_per_sp = rng.uniform(0.5, 1.5)
        estimated_days = round(sp * days_per_sp, 1)
        estimated_days = max(estimated_days, 0.5)

        # Actual days: log-normal around the estimate, biased ~20% over
        log_mean = math.log(estimated_days * 1.2)
        log_sigma = 0.3
        actual_days = round(float(rng.lognormal(log_mean, log_sigma)), 1)
        actual_days = max(actual_days, 0.5)

        # Calendar days: actual_days * calendar factor (1.2 - 2.0, centered ~1.5)
        cal_factor = rng.uniform(1.2, 2.0)
        calendar_days = max(1, round(actual_days * cal_factor))

        # Spread completed dates over ~12 months
        day_offset = int(rng.uniform(0, 365))
        completed = start_date + timedelta(days=day_offset)

        tasks.append({
            "id": f"TASK-{i + 1:03d}",
            "name": f"Task {i + 1}",
            "story_points": int(sp),
            "estimated_days": estimated_days,
            "actual_days": actual_days,
            "calendar_days": calendar_days,
            "completed_date": completed.isoformat(),
        })

    return {"team": team, "tasks": tasks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic team data for Horizon")
    parser.add_argument("--count", type=int, default=75, help="Number of tasks (default: 75)")
    parser.add_argument("--team", default="Demo Team", help="Team name (default: Demo Team)")
    parser.add_argument("--output", default="data/demo.json", help="Output path (default: data/demo.json)")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed (default: 0)")
    args = parser.parse_args()

    data = generate_tasks(args.count, args.team, args.seed)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Generated {args.count} tasks for '{args.team}' -> {args.output}")


if __name__ == "__main__":
    main()
