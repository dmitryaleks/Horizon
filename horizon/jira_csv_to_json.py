"""Convert Jira CSV exports to Horizon JSON format.

Edit the COLUMN_MAP below to match your Jira instance's column names.
"""

import warnings
from pathlib import Path

import pandas as pd

from horizon.data_store import load_team_data, merge_team_data, save_team_data
from horizon.models import Task, TeamData

# Map Jira CSV column names -> Horizon field names.
# Adjust these if your Jira instance uses custom field names.
COLUMN_MAP = {
    "Issue key": "id",
    "Summary": "name",
    "Story Points": "story_points",
    "Original Estimate": "estimated_hours",   # Jira stores hours
    "Time Spent": "actual_hours",             # Jira stores hours
    "Created": "created_date",
    "Resolved": "resolved_date",
}

HOURS_PER_DAY = 8.0


def convert(
    csv_path: Path,
    team_name: str,
    output_path: Path,
    append: bool = False,
) -> TeamData:
    """Read a Jira CSV export and produce a Horizon TeamData JSON file.

    Returns the resulting TeamData object.
    """
    df = pd.read_csv(csv_path)

    # Verify required columns exist
    missing = [col for col in COLUMN_MAP if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    df = df.rename(columns=COLUMN_MAP)

    tasks: list[Task] = []
    skipped = 0

    for idx, row in df.iterrows():
        # Skip rows with missing critical data
        required = ["id", "name", "story_points", "estimated_hours", "actual_hours", "resolved_date"]
        if any(pd.isna(row.get(f)) for f in required):
            skipped += 1
            warnings.warn(f"Row {idx}: skipping due to missing data (id={row.get('id', '?')})")
            continue

        try:
            estimated_days = float(row["estimated_hours"]) / HOURS_PER_DAY
            actual_days = float(row["actual_hours"]) / HOURS_PER_DAY

            if estimated_days <= 0 or actual_days <= 0:
                skipped += 1
                warnings.warn(f"Row {idx}: skipping zero/negative time values (id={row['id']})")
                continue

            created = pd.to_datetime(row["created_date"])
            resolved = pd.to_datetime(row["resolved_date"])

            if (resolved - created).days <= 0:
                skipped += 1
                warnings.warn(f"Row {idx}: skipping non-positive calendar days (id={row['id']})")
                continue

            task = Task(
                id=str(row["id"]),
                name=str(row["name"]),
                story_points=float(row["story_points"]),
                estimated_days=estimated_days,
                actual_days=actual_days,
                started_date=created.date(),
                completed_date=resolved.date(),
            )
            tasks.append(task)
        except (ValueError, TypeError) as e:
            skipped += 1
            warnings.warn(f"Row {idx}: skipping due to error: {e} (id={row.get('id', '?')})")

    if skipped > 0:
        print(f"Warning: skipped {skipped} rows with missing/invalid data")

    print(f"Imported {len(tasks)} tasks from CSV")

    if append and output_path.exists():
        existing = load_team_data(output_path)
        result = merge_team_data(existing, tasks)
    else:
        result = TeamData(team=team_name, tasks=tasks)

    save_team_data(result, output_path)
    return result
