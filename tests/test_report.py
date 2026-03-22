import pytest
from pathlib import Path

from horizon.models import (
    EstimationRequest,
    EstimationResult,
    PercentileEstimate,
    ReferenceCase,
    Task,
)
from horizon.report import generate_report, save_report


def make_result() -> EstimationResult:
    task = Task(
        id="PROJ-101",
        name="Implement auth",
        story_points=8,
        estimated_days=5.0,
        actual_days=7.0,
        started_date="2024-01-02",
        completed_date="2024-01-12",
    )
    return EstimationResult(
        request=EstimationRequest(
            task_name="Build search feature",
            story_points=5,
            initial_estimate_days=3.0,
        ),
        team_name="Team Alpha",
        effort_days=PercentileEstimate(p10=2.5, p50=4.2, p90=7.1),
        calendar_days=PercentileEstimate(p10=3.8, p50=6.5, p90=11.3),
        simulation_samples=[3.0, 4.0, 5.0, 4.5, 3.5] * 200,
        calendar_samples=[4.5, 6.0, 7.5, 6.8, 5.2] * 200,
        reference_cases=[
            ReferenceCase(task=task, similarity_score=0.85),
        ],
        dataset_size=15,
        timestamp="2025-03-22T10:00:00+00:00",
    )


class TestGenerateReport:
    def test_returns_html_string(self):
        html = generate_report(make_result())
        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")

    def test_contains_html_tags(self):
        html = generate_report(make_result())
        assert "<html" in html
        assert "</html>" in html

    def test_section_refined_estimate(self):
        html = generate_report(make_result())
        assert "Refined Effort Estimate" in html
        assert "4.2" in html  # P50

    def test_section_three_point(self):
        html = generate_report(make_result())
        assert "Three-Point Estimation" in html
        assert "PERT Weighted Average" in html

    def test_section_calendar_delivery(self):
        html = generate_report(make_result())
        assert "Calendar Delivery Estimate" in html
        assert "6.5" in html  # P50 calendar

    def test_section_reference_cases(self):
        html = generate_report(make_result())
        assert "Reference Cases" in html
        assert "PROJ-101" in html
        assert "Implement auth" in html
        assert "85%" in html

    def test_plotly_divs_present(self):
        html = generate_report(make_result())
        assert "effort-chart" in html
        assert "calendar-chart" in html
        assert "effort-cdf-chart" in html
        assert "calendar-cdf-chart" in html
        assert "Plotly.newPlot" in html

    def test_cdf_charts_have_hover_template(self):
        html = generate_report(make_result())
        assert "Cumulative Probability" in html
        assert "chance of finishing within" in html
        assert "buildCdfChart" in html

    def test_plotly_cdn_included(self):
        html = generate_report(make_result())
        assert "cdn.plot.ly" in html

    def test_task_name_in_title(self):
        html = generate_report(make_result())
        assert "Build search feature" in html

    def test_team_name_displayed(self):
        html = generate_report(make_result())
        assert "Team Alpha" in html

    def test_pert_value_computed(self):
        result = make_result()
        e = result.effort_days
        expected_pert = (e.p10 + 4 * e.p50 + e.p90) / 6  # (2.5 + 16.8 + 7.1) / 6 = 4.4
        html = generate_report(result)
        assert f"{expected_pert:.1f}" in html

    def test_empty_reference_cases(self):
        result = make_result()
        result = result.model_copy(update={"reference_cases": []})
        html = generate_report(result)
        assert "No reference cases available" in html


class TestSaveReport:
    def test_writes_file(self, tmp_path):
        html = generate_report(make_result())
        out = tmp_path / "report.html"
        save_report(html, out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_creates_parent_dirs(self, tmp_path):
        html = generate_report(make_result())
        out = tmp_path / "nested" / "dir" / "report.html"
        save_report(html, out)
        assert out.exists()
