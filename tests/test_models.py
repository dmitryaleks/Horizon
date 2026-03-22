import json
import pytest
from datetime import date
from pydantic import ValidationError

from horizon.models import (
    Task,
    TeamData,
    EstimationRequest,
    PercentileEstimate,
    ReferenceCase,
    EstimationResult,
)


# --- Fixtures ---

def make_task(**overrides) -> dict:
    base = {
        "id": "PROJ-1",
        "name": "Implement login",
        "story_points": 5,
        "estimated_days": 3.0,
        "actual_days": 4.5,
        "calendar_days": 7,
        "completed_date": "2025-01-15",
    }
    base.update(overrides)
    return base


# --- Task ---

def test_task_valid():
    t = Task(**make_task())
    assert t.id == "PROJ-1"
    assert t.story_points == 5
    assert t.completed_date == date(2025, 1, 15)


def test_task_float_story_points():
    t = Task(**make_task(story_points=2.5))
    assert t.story_points == 2.5


def test_task_missing_required_field():
    data = make_task()
    del data["actual_days"]
    with pytest.raises(ValidationError):
        Task(**data)


def test_task_negative_estimated_days():
    with pytest.raises(ValidationError):
        Task(**make_task(estimated_days=-1.0))


def test_task_zero_actual_days():
    with pytest.raises(ValidationError):
        Task(**make_task(actual_days=0.0))


def test_task_zero_calendar_days():
    with pytest.raises(ValidationError):
        Task(**make_task(calendar_days=0))


# --- TeamData ---

def test_team_data_valid():
    td = TeamData(team="Alpha", tasks=[Task(**make_task())])
    assert td.team == "Alpha"
    assert len(td.tasks) == 1


def test_team_data_empty_tasks():
    td = TeamData(team="Alpha", tasks=[])
    assert td.tasks == []


def test_team_data_json_round_trip():
    td = TeamData(team="Alpha", tasks=[Task(**make_task()), Task(**make_task(id="PROJ-2"))])
    json_str = td.model_dump_json()
    td2 = TeamData.model_validate_json(json_str)
    assert td2.team == td.team
    assert len(td2.tasks) == 2
    assert td2.tasks[0].id == "PROJ-1"
    assert td2.tasks[1].id == "PROJ-2"


def test_team_data_serializes_date_correctly():
    td = TeamData(team="Alpha", tasks=[Task(**make_task())])
    data = json.loads(td.model_dump_json())
    assert data["tasks"][0]["completed_date"] == "2025-01-15"


# --- EstimationRequest ---

def test_estimation_request_valid():
    req = EstimationRequest(task_name="New feature", story_points=8, initial_estimate_days=5.0)
    assert req.story_points == 8


def test_estimation_request_float_story_points():
    req = EstimationRequest(task_name="Task", story_points=3.5, initial_estimate_days=2.0)
    assert req.story_points == 3.5


def test_estimation_request_zero_estimate():
    with pytest.raises(ValidationError):
        EstimationRequest(task_name="Task", story_points=5, initial_estimate_days=0.0)


def test_estimation_request_negative_estimate():
    with pytest.raises(ValidationError):
        EstimationRequest(task_name="Task", story_points=5, initial_estimate_days=-1.0)


# --- PercentileEstimate ---

def test_percentile_estimate_valid():
    pe = PercentileEstimate(p10=2.0, p50=4.0, p90=8.0)
    assert pe.p10 == 2.0
    assert pe.p50 == 4.0
    assert pe.p90 == 8.0


# --- ReferenceCase ---

def test_reference_case_valid():
    rc = ReferenceCase(task=Task(**make_task()), similarity_score=0.95)
    assert rc.similarity_score == 0.95


# --- EstimationResult ---

def make_estimation_result() -> EstimationResult:
    task = Task(**make_task())
    return EstimationResult(
        request=EstimationRequest(task_name="New task", story_points=5, initial_estimate_days=3.0),
        team_name="Alpha",
        effort_days=PercentileEstimate(p10=2.0, p50=4.0, p90=7.0),
        calendar_days=PercentileEstimate(p10=3.0, p50=6.0, p90=11.0),
        simulation_samples=[3.0, 4.0, 5.0],
        calendar_samples=[4.5, 6.0, 7.5],
        reference_cases=[ReferenceCase(task=task, similarity_score=1.0)],
        dataset_size=15,
        timestamp="2025-01-20T10:00:00",
    )


def test_estimation_result_valid():
    result = make_estimation_result()
    assert result.team_name == "Alpha"
    assert result.dataset_size == 15


def test_estimation_result_json_round_trip():
    result = make_estimation_result()
    json_str = result.model_dump_json()
    result2 = EstimationResult.model_validate_json(json_str)
    assert result2.team_name == result.team_name
    assert result2.effort_days.p50 == result.effort_days.p50
    assert result2.reference_cases[0].task.id == "PROJ-1"
