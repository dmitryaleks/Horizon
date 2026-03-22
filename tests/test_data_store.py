import json
import pytest
from pathlib import Path

from horizon.data_store import load_team_data, save_team_data, merge_team_data
from horizon.models import Task, TeamData

FIXTURE = Path(__file__).parent / "fixtures" / "sample_team.json"


def make_task(id: str = "PROJ-1", story_points: int = 5) -> Task:
    return Task(
        id=id,
        name=f"Task {id}",
        story_points=story_points,
        estimated_days=3.0,
        actual_days=4.0,
        started_date="2024-05-26",
        completed_date="2024-06-01",
    )


# --- load_team_data ---

def test_load_valid_fixture():
    td = load_team_data(FIXTURE)
    assert td.team == "Team Alpha"
    assert len(td.tasks) == 15


def test_load_returns_team_data_type():
    td = load_team_data(FIXTURE)
    assert isinstance(td, TeamData)
    assert isinstance(td.tasks[0], Task)


def test_load_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_team_data(Path("nonexistent_file.json"))


def test_load_invalid_schema(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"team": "X", "tasks": [{"id": "1"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid data file"):
        load_team_data(bad)


def test_load_malformed_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_team_data(bad)


# --- save_team_data ---

def test_save_and_reload(tmp_path):
    td = TeamData(team="Beta", tasks=[make_task("T-1"), make_task("T-2")])
    out = tmp_path / "output.json"
    save_team_data(td, out)
    assert out.exists()
    td2 = load_team_data(out)
    assert td2.team == "Beta"
    assert len(td2.tasks) == 2


def test_save_creates_parent_dirs(tmp_path):
    out = tmp_path / "nested" / "dir" / "team.json"
    td = TeamData(team="Gamma", tasks=[make_task()])
    save_team_data(td, out)
    assert out.exists()


def test_save_writes_valid_json(tmp_path):
    td = TeamData(team="Delta", tasks=[make_task()])
    out = tmp_path / "team.json"
    save_team_data(td, out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["team"] == "Delta"
    assert raw["tasks"][0]["id"] == "PROJ-1"


# --- merge_team_data ---

def test_merge_adds_new_tasks():
    existing = TeamData(team="Alpha", tasks=[make_task("T-1"), make_task("T-2")])
    new_tasks = [make_task("T-3"), make_task("T-4")]
    merged = merge_team_data(existing, new_tasks)
    assert len(merged.tasks) == 4


def test_merge_deduplicates_by_id():
    existing = TeamData(team="Alpha", tasks=[make_task("T-1"), make_task("T-2")])
    new_tasks = [make_task("T-2"), make_task("T-3")]  # T-2 is a duplicate
    merged = merge_team_data(existing, new_tasks)
    assert len(merged.tasks) == 3
    ids = [t.id for t in merged.tasks]
    assert ids.count("T-2") == 1


def test_merge_preserves_team_name():
    existing = TeamData(team="Alpha", tasks=[make_task("T-1")])
    merged = merge_team_data(existing, [make_task("T-2")])
    assert merged.team == "Alpha"


def test_merge_empty_new_tasks():
    existing = TeamData(team="Alpha", tasks=[make_task("T-1")])
    merged = merge_team_data(existing, [])
    assert len(merged.tasks) == 1


def test_merge_all_duplicates():
    existing = TeamData(team="Alpha", tasks=[make_task("T-1"), make_task("T-2")])
    merged = merge_team_data(existing, [make_task("T-1"), make_task("T-2")])
    assert len(merged.tasks) == 2
