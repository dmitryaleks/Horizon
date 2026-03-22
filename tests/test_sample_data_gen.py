import json
import pytest
from pathlib import Path

from gluecode.sample_data_gen import generate_tasks
from horizon.data_store import load_team_data


class TestGenerateTasks:
    def test_correct_count(self):
        data = generate_tasks(50, "Test")
        assert len(data["tasks"]) == 50

    def test_team_name(self):
        data = generate_tasks(10, "Alpha")
        assert data["team"] == "Alpha"

    def test_valid_horizon_json(self, tmp_path):
        data = generate_tasks(25, "Test", seed=42)
        out = tmp_path / "test.json"
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        td = load_team_data(out)
        assert len(td.tasks) == 25
        assert td.team == "Test"

    def test_positive_values(self):
        data = generate_tasks(100, "Test", seed=99)
        for t in data["tasks"]:
            assert t["estimated_days"] > 0
            assert t["actual_days"] > 0
            assert "started_date" in t
            assert "completed_date" in t
            assert t["story_points"] in [1, 2, 3, 5, 8, 13]

    def test_deterministic_with_seed(self):
        d1 = generate_tasks(20, "Test", seed=42)
        d2 = generate_tasks(20, "Test", seed=42)
        assert d1 == d2

    def test_produces_reasonable_estimation(self, tmp_path):
        """Generated data should work with the estimation pipeline."""
        from horizon.models import EstimationRequest
        from horizon.simulation import run_estimation

        data = generate_tasks(75, "Demo", seed=7)
        out = tmp_path / "demo.json"
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        td = load_team_data(out)

        req = EstimationRequest(task_name="New feature", story_points=5, initial_estimate_days=3.0)
        result = run_estimation(req, td.tasks, team_name=td.team, iterations=5000, seed=42)

        assert result.effort_days.p10 > 0
        assert result.effort_days.p10 < result.effort_days.p50 < result.effort_days.p90
        assert result.calendar_days.p50 > 0
        assert len(result.reference_cases) == 5
