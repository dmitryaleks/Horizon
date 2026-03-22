import pytest
from pathlib import Path

from horizon.cli import build_parser, cmd_estimate, cmd_validate

FIXTURE = Path(__file__).parent / "fixtures" / "sample_team.json"


class TestArgParsing:
    def test_estimate_all_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "estimate",
            "--data", "data/team.json",
            "--name", "My task",
            "--story-points", "8",
            "--estimate", "5.0",
            "--output", "out.html",
            "--iterations", "5000",
            "--sigma", "3.0",
            "--seed", "42",
            "--top-references", "3",
        ])
        assert args.command == "estimate"
        assert args.data == "data/team.json"
        assert args.name == "My task"
        assert args.story_points == 8.0
        assert args.estimate == 5.0
        assert args.output == "out.html"
        assert args.iterations == 5000
        assert args.sigma == 3.0
        assert args.seed == 42
        assert args.top_references == 3

    def test_estimate_defaults(self):
        parser = build_parser()
        args = parser.parse_args([
            "estimate",
            "--data", "d.json",
            "--name", "T",
            "--story-points", "5",
            "--estimate", "3",
        ])
        assert args.output == "report.html"
        assert args.iterations == 10000
        assert args.sigma == 2.5
        assert args.seed is None
        assert args.top_references == 5

    def test_import_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "import",
            "--csv", "export.csv",
            "--team", "Alpha",
            "--output", "out.json",
            "--append",
        ])
        assert args.command == "import"
        assert args.csv == "export.csv"
        assert args.team == "Alpha"
        assert args.append is True

    def test_validate_args(self):
        parser = build_parser()
        args = parser.parse_args(["validate", "--data", "data/team.json"])
        assert args.command == "validate"
        assert args.data == "data/team.json"

    def test_no_command_returns_none(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestCmdEstimate:
    def test_produces_html_report(self, tmp_path):
        parser = build_parser()
        out = tmp_path / "test_report.html"
        args = parser.parse_args([
            "estimate",
            "--data", str(FIXTURE),
            "--name", "Test task",
            "--story-points", "5",
            "--estimate", "3.0",
            "--output", str(out),
            "--iterations", "1000",
            "--seed", "42",
        ])
        cmd_estimate(args)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Test task" in content
        assert "Team Alpha" in content

    def test_console_output(self, tmp_path, capsys):
        parser = build_parser()
        out = tmp_path / "report.html"
        args = parser.parse_args([
            "estimate",
            "--data", str(FIXTURE),
            "--name", "My feature",
            "--story-points", "8",
            "--estimate", "5.0",
            "--output", str(out),
            "--iterations", "500",
            "--seed", "1",
        ])
        cmd_estimate(args)
        captured = capsys.readouterr()
        assert "My feature" in captured.out
        assert "Team Alpha" in captured.out
        assert "P50" in captured.out
        assert "Report saved to" in captured.out


class TestCmdValidate:
    def test_prints_stats(self, capsys):
        parser = build_parser()
        args = parser.parse_args(["validate", "--data", str(FIXTURE)])
        cmd_validate(args)
        captured = capsys.readouterr()
        assert "Team: Team Alpha" in captured.out
        assert "Tasks: 15" in captured.out
        assert "Validation: OK" in captured.out
        assert "Story points distribution" in captured.out
        assert "Actual/Estimated ratio" in captured.out
