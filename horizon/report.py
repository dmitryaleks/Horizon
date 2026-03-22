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

    html = template.render(
        result=result,
        pert_effort=pert_effort,
        pert_calendar=pert_calendar,
        effort_samples_json=json.dumps(result.simulation_samples),
        calendar_samples_json=json.dumps(result.calendar_samples),
        version=__version__,
    )
    return html


def save_report(html: str, filepath: Path) -> None:
    """Write HTML report to file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
