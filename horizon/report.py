import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from horizon import __version__
from horizon.models import EstimationResult

TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_report(result: EstimationResult) -> str:
    """Produce a self-contained HTML dashboard from an EstimationResult."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)
    template = env.get_template("dashboard.html")

    e = result.effort_days
    c = result.calendar_days
    pert_effort = (e.p10 + 4 * e.p50 + e.p90) / 6
    pert_calendar = (c.p10 + 4 * c.p50 + c.p90) / 6

    # Serialize influential tasks for JS
    influential_json = json.dumps([
        {
            "id": it.task.id,
            "name": it.task.name,
            "story_points": it.task.story_points,
            "ratio": round(it.task.actual_days / it.task.estimated_days, 2),
            "weight": round(it.weight * 100, 1),
        }
        for it in result.influential_tasks
    ])

    # Serialize reference cases for scatter plot
    ref_scatter_json = json.dumps([
        {
            "id": rc.task.id,
            "name": rc.task.name,
            "story_points": rc.task.story_points,
            "estimated": rc.task.estimated_days,
            "actual": rc.task.actual_days,
            "similarity": round(rc.similarity_score * 100),
        }
        for rc in result.reference_cases
    ])

    html = template.render(
        result=result,
        pert_effort=pert_effort,
        pert_calendar=pert_calendar,
        effort_samples_json=json.dumps(result.simulation_samples),
        calendar_samples_json=json.dumps(result.calendar_samples),
        influential_json=influential_json,
        ref_scatter_json=ref_scatter_json,
        version=__version__,
    )
    return html


def save_report(html: str, filepath: Path) -> None:
    """Write HTML report to file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
