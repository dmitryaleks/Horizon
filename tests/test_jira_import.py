import pytest
from pathlib import Path

from horizon.data_store import load_team_data
from horizon.jira_csv_to_json import convert

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "sample_jira_export.csv"


class TestJiraImport:
    def test_basic_import(self, tmp_path):
        out = tmp_path / "team.json"
        result = convert(FIXTURE_CSV, "Test Team", out)
        assert len(result.tasks) == 10
        assert result.team == "Test Team"
        assert out.exists()

    def test_roundtrip_via_load(self, tmp_path):
        out = tmp_path / "team.json"
        convert(FIXTURE_CSV, "Test Team", out)
        td = load_team_data(out)
        assert td.team == "Test Team"
        assert len(td.tasks) == 10

    def test_hours_to_days_conversion(self, tmp_path):
        out = tmp_path / "team.json"
        result = convert(FIXTURE_CSV, "Test", out)
        # PROJ-201: Original Estimate=24h -> 3.0 days, Time Spent=32h -> 4.0 days
        t = next(t for t in result.tasks if t.id == "PROJ-201")
        assert t.estimated_days == pytest.approx(3.0)
        assert t.actual_days == pytest.approx(4.0)

    def test_calendar_days_computed(self, tmp_path):
        out = tmp_path / "team.json"
        result = convert(FIXTURE_CSV, "Test", out)
        # PROJ-201: Created 2024-01-05, Resolved 2024-01-12 -> 7 calendar days
        t = next(t for t in result.tasks if t.id == "PROJ-201")
        assert t.calendar_days == 7

    def test_dates_from_jira(self, tmp_path):
        out = tmp_path / "team.json"
        result = convert(FIXTURE_CSV, "Test", out)
        t = next(t for t in result.tasks if t.id == "PROJ-201")
        assert str(t.started_date) == "2024-01-05"
        assert str(t.completed_date) == "2024-01-12"

    def test_append_merges(self, tmp_path):
        out = tmp_path / "team.json"
        convert(FIXTURE_CSV, "Test", out)
        # Re-import with append - should deduplicate
        result = convert(FIXTURE_CSV, "Test", out, append=True)
        assert len(result.tasks) == 10  # no duplicates

    def test_missing_column_raises(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("Col1,Col2\na,b\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Missing columns"):
            convert(bad_csv, "Test", tmp_path / "out.json")

    def test_skips_rows_with_missing_data(self, tmp_path):
        csv = tmp_path / "partial.csv"
        csv.write_text(
            "Issue key,Summary,Story Points,Original Estimate,Time Spent,Created,Resolved\n"
            "T-1,Good task,5,24,32,2024-01-01,2024-01-08\n"
            "T-2,Bad task,,16,20,2024-01-01,2024-01-05\n",
            encoding="utf-8",
        )
        out = tmp_path / "team.json"
        result = convert(csv, "Test", out)
        assert len(result.tasks) == 1
        assert result.tasks[0].id == "T-1"
