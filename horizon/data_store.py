import json
from pathlib import Path

from pydantic import ValidationError

from horizon.models import Task, TeamData


def load_team_data(filepath: Path) -> TeamData:
    """Load and validate a team JSON file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    try:
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in '{filepath}': {e}") from e
    try:
        return TeamData.model_validate(parsed)
    except ValidationError as e:
        raise ValueError(f"Invalid data file '{filepath}':\n{e}") from e


def save_team_data(data: TeamData, filepath: Path) -> None:
    """Write a TeamData object to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.model_dump_json(indent=2), encoding="utf-8")


def merge_team_data(existing: TeamData, new_tasks: list[Task]) -> TeamData:
    """Merge new tasks into existing data, deduplicating by task id."""
    existing_ids = {t.id for t in existing.tasks}
    merged = list(existing.tasks) + [t for t in new_tasks if t.id not in existing_ids]
    return TeamData(team=existing.team, tasks=merged)
