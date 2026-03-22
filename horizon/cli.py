import argparse
import sys
from pathlib import Path

from horizon import __version__
from horizon.data_store import load_team_data
from horizon.jira_csv_to_json import convert as jira_convert
from horizon.models import EstimationRequest
from horizon.report import generate_report, save_report
from horizon.simulation import run_estimation

MIN_RECOMMENDED_TASKS = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="horizon",
        description=f"Horizon Monte Carlo Estimation Engine v{__version__}",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    # --- estimate ---
    est = sub.add_parser("estimate", help="Estimate effort for a new task")
    est.add_argument("--data", required=True, help="Path to team historical JSON file")
    est.add_argument("--name", required=True, help="Name of the task being estimated")
    est.add_argument("--story-points", required=True, type=float, help="Story points for the new task")
    est.add_argument("--estimate", required=True, type=float, help="Initial estimate in man-days")
    est.add_argument("--output", default="report.html", help="Output HTML report path (default: report.html)")
    est.add_argument("--iterations", type=int, default=10000, help="Monte Carlo iterations (default: 10000)")
    est.add_argument("--sigma", type=float, default=2.5, help="Gaussian weighting sigma (default: 2.5)")
    est.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    est.add_argument("--top-references", type=int, default=5, help="Number of reference cases (default: 5)")
    est.add_argument("--verbose", action="store_true", help="Print progress and extra statistics")

    # --- import ---
    imp = sub.add_parser("import", help="Import Jira CSV export to Horizon JSON")
    imp.add_argument("--csv", required=True, help="Path to Jira CSV export")
    imp.add_argument("--team", required=True, help="Team name for the JSON file")
    imp.add_argument("--output", required=True, help="Output JSON file path")
    imp.add_argument("--append", action="store_true", help="Merge into existing file")

    # --- validate ---
    val = sub.add_parser("validate", help="Validate a team data file")
    val.add_argument("--data", required=True, help="Path to team historical JSON file")

    return parser


def cmd_estimate(args: argparse.Namespace) -> None:
    verbose = args.verbose

    if verbose:
        print(f"Loading data from {args.data}...")

    try:
        td = load_team_data(Path(args.data))
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if len(td.tasks) < MIN_RECOMMENDED_TASKS:
        print(
            f"Warning: only {len(td.tasks)} historical tasks found. "
            f"At least {MIN_RECOMMENDED_TASKS} are recommended for reliable estimates.",
            file=sys.stderr,
        )

    # Check if story points are within historical range
    sp_values = [t.story_points for t in td.tasks]
    sp_min, sp_max = min(sp_values), max(sp_values)
    if args.story_points < sp_min or args.story_points > sp_max:
        print(
            f"Warning: story points ({args.story_points}) are outside the historical range "
            f"[{sp_min}, {sp_max}]. Estimates may be less reliable.",
            file=sys.stderr,
        )

    request = EstimationRequest(
        task_name=args.name,
        story_points=args.story_points,
        initial_estimate_days=args.estimate,
    )

    if verbose:
        print(f"Running {args.iterations} Monte Carlo iterations (sigma={args.sigma})...")

    result = run_estimation(
        request=request,
        historical_tasks=td.tasks,
        team_name=td.team,
        iterations=args.iterations,
        sigma=args.sigma,
        seed=args.seed,
        top_references=args.top_references,
    )

    if verbose:
        print("Generating HTML report...")

    html = generate_report(result)
    save_report(html, Path(args.output))

    print(f"Task: {result.request.task_name}")
    print(f"Team: {result.team_name} ({result.dataset_size} historical tasks)")
    print()
    print("Effort estimate (man-days):")
    print(f"  Optimistic (P10): {result.effort_days.p10:.1f}")
    print(f"  Most Likely (P50): {result.effort_days.p50:.1f}")
    print(f"  Pessimistic (P90): {result.effort_days.p90:.1f}")
    pert_effort = (result.effort_days.p10 + 4 * result.effort_days.p50 + result.effort_days.p90) / 6
    print(f"  PERT Average:     {pert_effort:.1f}")
    print()
    print("Calendar estimate (days):")
    print(f"  Optimistic (P10): {result.calendar_days.p10:.1f}")
    print(f"  Most Likely (P50): {result.calendar_days.p50:.1f}")
    print(f"  Pessimistic (P90): {result.calendar_days.p90:.1f}")
    pert_cal = (result.calendar_days.p10 + 4 * result.calendar_days.p50 + result.calendar_days.p90) / 6
    print(f"  PERT Average:     {pert_cal:.1f}")
    print()

    if verbose and result.reference_cases:
        print("Top reference cases:")
        for rc in result.reference_cases:
            print(
                f"  {rc.task.id}: {rc.task.name} "
                f"(SP={rc.task.story_points}, est={rc.task.estimated_days:.1f}d, "
                f"actual={rc.task.actual_days:.1f}d, similarity={rc.similarity_score:.0%})"
            )
        print()

    print(f"Report saved to: {args.output}")


def cmd_import(args: argparse.Namespace) -> None:
    try:
        result = jira_convert(
            csv_path=Path(args.csv),
            team_name=args.team,
            output_path=Path(args.output),
            append=args.append,
        )
        print(f"Saved {len(result.tasks)} tasks to {args.output}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    try:
        td = load_team_data(Path(args.data))
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    sp_values = [t.story_points for t in td.tasks]
    ratios = [t.actual_days / t.estimated_days for t in td.tasks]
    cal_ratios = [t.calendar_days / t.actual_days for t in td.tasks]

    print(f"Team: {td.team}")
    print(f"Tasks: {len(td.tasks)}")
    print()

    if td.tasks:
        dates = sorted(t.completed_date for t in td.tasks)
        print(f"Date range: {dates[0]} to {dates[-1]}")
        print()
        print("Story points distribution:")
        print(f"  Min: {min(sp_values)}, Max: {max(sp_values)}, Mean: {sum(sp_values)/len(sp_values):.1f}")
        print()
        print("Actual/Estimated ratio:")
        print(f"  Min: {min(ratios):.2f}, Max: {max(ratios):.2f}, Mean: {sum(ratios)/len(ratios):.2f}")
        print()
        print("Calendar/Actual ratio:")
        print(f"  Min: {min(cal_ratios):.2f}, Max: {max(cal_ratios):.2f}, Mean: {sum(cal_ratios)/len(cal_ratios):.2f}")
        print()

        if len(td.tasks) < MIN_RECOMMENDED_TASKS:
            print(
                f"Warning: only {len(td.tasks)} tasks. "
                f"At least {MIN_RECOMMENDED_TASKS} recommended.",
                file=sys.stderr,
            )

    print("Validation: OK")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "estimate": cmd_estimate,
        "import": cmd_import,
        "validate": cmd_validate,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
