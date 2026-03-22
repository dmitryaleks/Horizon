# Horizon

**Monte Carlo Estimation Engine for Software Teams**

Horizon replaces gut-feel task estimates with data-driven probabilistic forecasts. It uses your team's historical task data — story points, initial estimates, actual effort, and calendar duration — to run 10,000 Monte Carlo simulations and produce confidence intervals for both effort (man-days) and calendar delivery (elapsed days). Output is a self-contained interactive HTML dashboard.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [CLI Commands](#cli-commands)
  - [estimate](#estimate)
  - [import](#import)
  - [validate](#validate)
- [Data Format](#data-format)
  - [Team Data JSON](#team-data-json)
  - [Jira CSV Import](#jira-csv-import)
- [HTML Report](#html-report)
- [Methodology](#methodology)
- [Utilities](#utilities)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Dependencies](#dependencies)
- [License](#license)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate sample data
python gluecode/sample_data_gen.py --count 256 --team "Demo Team" --output data/demo_team.json --seed 42

# Run an estimation
python main.py estimate --data data/demo_team.json --name "Build search feature" --story-points 8 --estimate 15.0 --output reports/estimate_report.html --seed 42

# Open the report
start reports/estimate_report.html
```

Example console output:

```
Task: Build search feature
Team: Demo Team (75 historical tasks)

Effort estimate (man-days):
  Optimistic (P10): 2.4
  Most Likely (P50): 3.5
  Pessimistic (P90): 4.9
  PERT Average:     3.5

Calendar estimate (days):
  Optimistic (P10): 3.7
  Most Likely (P50): 5.3
  Pessimistic (P90): 8.5
  PERT Average:     5.6

Report saved to: reports/estimate_report.html
```

---

## Installation

Requires **Python 3.10+**.

```bash
# Clone the repository
git clone https://github.com/dmitryaleks/Horizon.git
cd Horizon

# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # macOS/Linux

# Install runtime dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing)
pip install -r requirements-dev.txt
```

---

## CLI Commands

All commands are run through `main.py`:

```bash
python main.py <command> [options]
```

### estimate

Run a Monte Carlo estimation for a new task.

```bash
python main.py estimate \
  --data <path-to-team-json> \
  --name "Task name" \
  --story-points <number> \
  --estimate <man-days> \
  --output <report.html> \
  [--iterations 10000] \
  [--sigma 2.5] \
  [--seed 42] \
  [--top-references 5] \
  [--verbose]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--data` | Yes | — | Path to team historical data JSON file |
| `--name` | Yes | — | Name of the task being estimated |
| `--story-points` | Yes | — | Story points for the new task |
| `--estimate` | Yes | — | Initial effort estimate in man-days |
| `--output` | No | `report.html` | Output HTML report file path |
| `--iterations` | No | `10000` | Number of Monte Carlo iterations |
| `--sigma` | No | `2.5` | Gaussian kernel bandwidth (story points) |
| `--seed` | No | Random | RNG seed for reproducible results |
| `--top-references` | No | `5` | Number of similar historical tasks to show |
| `--verbose` | No | Off | Print progress info and reference case details |

### import

Import a Jira CSV export into Horizon's JSON format.

```bash
python main.py import \
  --csv <jira-export.csv> \
  --team "Team Name" \
  --output <team-data.json> \
  [--append]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--csv` | Yes | — | Path to Jira CSV export file |
| `--team` | Yes | — | Team name for the output JSON |
| `--output` | Yes | — | Output JSON file path |
| `--append` | No | Off | Merge into an existing JSON file (deduplicates by task ID) |

The importer expects standard Jira column names. To customize, edit the `COLUMN_MAP` dictionary at the top of `horizon/jira_csv_to_json.py`.

### validate

Validate a team data file and print dataset statistics.

```bash
python main.py validate --data <team-data.json>
```

Prints: team name, task count, date range, story point distribution, actual/estimated ratio stats, and calendar/actual ratio stats.

---

## Data Format

### Team Data JSON

Horizon stores historical task data in a simple JSON format:

```json
{
  "team": "Team Alpha",
  "tasks": [
    {
      "id": "PROJ-101",
      "name": "Implement user authentication",
      "story_points": 8,
      "estimated_days": 5.0,
      "actual_days": 7.0,
      "started_date": "2024-01-02",
      "completed_date": "2024-01-12"
    }
  ]
}
```

**Field reference:**

| Field | Type | Description |
|-------|------|-------------|
| `team` | string | Team or project name |
| `tasks` | array | List of completed historical tasks |
| `tasks[].id` | string | Unique task identifier (e.g., Jira issue key) |
| `tasks[].name` | string | Task name or summary |
| `tasks[].story_points` | number | Story points assigned to the task (integer or float) |
| `tasks[].estimated_days` | number | Original effort estimate in man-days (must be > 0) |
| `tasks[].actual_days` | number | Actual effort spent in man-days (must be > 0) |
| `tasks[].started_date` | string | Date work began, ISO 8601 format (`YYYY-MM-DD`) |
| `tasks[].completed_date` | string | Date work was completed, ISO 8601 format (`YYYY-MM-DD`) |

Calendar days (elapsed time from start to completion) are computed automatically as `completed_date - started_date`.

**Minimum data requirements:** At least 5 tasks are required. For reliable estimates, 15-20+ tasks are recommended, ideally with a spread of story point sizes.

### Jira CSV Import

The `import` command reads standard Jira CSV exports with these columns:

| Jira Column | Horizon Field | Notes |
|-------------|---------------|-------|
| `Issue key` | `id` | Task identifier |
| `Summary` | `name` | Task name |
| `Story Points` | `story_points` | Numeric story points |
| `Original Estimate` | `estimated_days` | Converted from hours to days (÷ 8) |
| `Time Spent` | `actual_days` | Converted from hours to days (÷ 8) |
| `Created` | `started_date` | Used as the task start date |
| `Resolved` | `completed_date` | Used as the task completion date |

Rows with missing critical fields (story points, estimates, dates) are skipped with a warning. To adapt to custom Jira field names, edit the `COLUMN_MAP` in `horizon/jira_csv_to_json.py`.

Example CSV:

```csv
Issue key,Summary,Story Points,Original Estimate,Time Spent,Created,Resolved
PROJ-201,Build login page,5,24,32,2024-01-05,2024-01-12
PROJ-202,Add password reset,3,16,20,2024-01-10,2024-01-15
```

---

## HTML Report

The `estimate` command generates a self-contained HTML dashboard with four sections:

1. **Refined Effort Estimate** — P10/P50/P90 effort-days table with an interactive histogram and CDF chart showing the probability distribution of effort outcomes.

2. **Three-Point Estimation** — Optimistic (P10), Most Likely (P50), and Pessimistic (P90) values plus the PERT weighted average: `(P10 + 4 × P50 + P90) / 6`.

3. **Calendar Delivery Estimate** — P10/P50/P90 calendar-days table with an interactive histogram and CDF chart. Calendar estimates account for weekends, meetings, and other overhead based on historical patterns.

4. **Reference Cases** — The most similar historical tasks ranked by story-point similarity, showing their estimates, actuals, and similarity scores.

All charts are interactive (powered by Plotly) with hover details. The report is a single `.html` file with no external dependencies — it can be shared, archived, or opened offline.

---

## Methodology

Horizon uses **weighted bootstrap Monte Carlo simulation** to produce probabilistic estimates:

1. **Compute estimation accuracy ratios** from historical tasks: `actual_days / estimated_days`.
2. **Weight** historical tasks by story-point similarity using a Gaussian kernel.
3. **Bootstrap-sample** 10,000 ratios (weighted, with replacement) and multiply each by the initial estimate.
4. **Extract percentiles** (P10, P50, P90) from the simulated distribution.
5. **Estimate calendar days** by independently sampling calendar-to-effort ratios from history.
6. **Find reference cases** — the most similar past tasks for qualitative anchoring.

For the full technical specification with formulas and a worked numerical example, see **[METHODOLOGY.md](METHODOLOGY.md)**.

For a long-form narrative exploring the intellectual history and broader landscape of these techniques — Kahneman's planning fallacy, Efron's bootstrap, Monte Carlo methods from nuclear physics, and the Cold War origins of PERT — see **[DEEP_DIVE.md](DEEP_DIVE.md)**.

---

## Utilities

### Sample Data Generator

Generate synthetic historical task data for testing or demos:

```bash
python gluecode/sample_data_gen.py \
  --count 75 \
  --team "Demo Team" \
  --output data/demo_team.json \
  --seed 42
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--count` | 75 | Number of tasks to generate |
| `--team` | "Demo Team" | Team name |
| `--output` | `data/demo.json` | Output path |
| `--seed` | 0 | RNG seed for reproducibility |

Generated tasks use Fibonacci story points (1, 2, 3, 5, 8, 13), log-normal actual durations biased ~20% above estimates, and calendar factors between 1.2x and 2.0x. Dates are spread over 12 months.

---

## Project Structure

```
Horizon/
├── main.py                          # CLI entry point
├── requirements.txt                 # Runtime dependencies
├── requirements-dev.txt             # Test dependencies
├── METHODOLOGY.md                   # Technical methodology reference
├── DEEP_DIVE.md                     # Long-form narrative essay
├── horizon/
│   ├── __init__.py                  # Package version
│   ├── cli.py                       # Argparse CLI (estimate, import, validate)
│   ├── models.py                    # Pydantic data models
│   ├── data_store.py                # JSON I/O (load, save, merge)
│   ├── simulation.py                # Monte Carlo estimation pipeline
│   ├── mc_utils.py                  # Shared MC helpers (ratios, weights, bootstrap)
│   ├── calendar_estimator.py        # Effort-to-calendar-days conversion
│   ├── reference_finder.py          # Similar historical task finder
│   ├── jira_csv_to_json.py          # Jira CSV importer
│   ├── report.py                    # HTML report generator
│   └── templates/
│       └── dashboard.html           # Jinja2 report template
├── gluecode/
│   └── sample_data_gen.py           # Synthetic data generator
├── data/
│   └── demo_team.json               # Example generated dataset
├── reports/
│   └── estimate_report.html         # Example generated report
└── tests/
    ├── fixtures/
    │   ├── sample_team.json          # 15-task test fixture
    │   └── sample_jira_export.csv    # 10-row Jira CSV fixture
    ├── test_models.py
    ├── test_data_store.py
    ├── test_simulation.py
    ├── test_calendar_estimator.py
    ├── test_reference_finder.py
    ├── test_report.py
    ├── test_cli.py
    ├── test_jira_import.py
    └── test_sample_data_gen.py
```

---

## Testing

Run the full test suite (110 tests):

```bash
pytest tests/ -v
```

With coverage report:

```bash
pytest --cov=horizon tests/
```

Tests cover: data models and validation, JSON I/O round-trips, Monte Carlo simulation determinism and statistical properties, calendar estimation, reference case ranking, HTML report generation, CLI argument parsing, Jira import, and a full end-to-end pipeline integration test.

---

## Dependencies

**Runtime:**

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | >= 1.26 | Array operations, bootstrap sampling, percentiles |
| pydantic | >= 2.5 | Data validation and JSON serialization |
| plotly | >= 5.18 | Interactive charts in HTML reports |
| jinja2 | >= 3.1 | HTML template rendering |
| pandas | >= 2.1 | CSV reading for Jira import |

**Development:**

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >= 7.4 | Test framework |
| pytest-cov | >= 4.1 | Coverage reporting |

---

## License

This project is for internal team use.
