# Horizon: Monte Carlo Effort Estimation Engine - Project Plan

## Context

The team needs a data-driven estimation tool that replaces gut-feel estimates with Monte Carlo simulations grounded in historical task data. The tool takes a team's past Jira task history (story points, estimates, actuals, calendar durations) and uses bootstrap resampling to produce statistically rigorous effort and calendar-day estimates with confidence intervals. Output is a self-contained HTML dashboard with interactive Plotly charts.

**Key constraints:** Internal CLI tool, Python 3.10+, single-task estimation, medium data scale (50-500 tasks), Plotly charts, Jira CSV import.

---

## Architecture Overview

```
main.py (entry point)
  -> horizon/cli.py (argparse dispatch)
       -> horizon/data_store.py (JSON I/O)
       -> horizon/simulation.py (MC engine)
            -> horizon/calendar_estimator.py (effort -> calendar days)
            -> horizon/reference_finder.py (similar past tasks)
       -> horizon/report.py + templates/dashboard.html (HTML output)

gluecode/
  -> jira_csv_to_json.py (Jira CSV importer)
  -> sample_data_gen.py (synthetic test data)
```

**Core algorithm:** Weighted bootstrap resampling of historical actual/estimated ratios, with Gaussian similarity weighting by story points (sigma=2.5), 10,000 iterations. Output: P10/P50/P90 percentiles for both effort-days and calendar-days.

---

## Directory Structure

```
Horizon/
|-- main.py                          # CLI entry point
|-- requirements.txt                 # numpy, pydantic, plotly, jinja2, pandas
|-- requirements-dev.txt             # pytest, pytest-cov
|-- horizon/
|   |-- __init__.py
|   |-- cli.py                       # argparse with estimate/import/validate commands
|   |-- models.py                    # Pydantic models (Task, TeamData, EstimationRequest, EstimationResult)
|   |-- data_store.py                # Load/save/validate JSON data files
|   |-- simulation.py                # Monte Carlo bootstrap engine
|   |-- calendar_estimator.py        # Calendar-day projection from effort estimates
|   |-- reference_finder.py          # Find most similar historical tasks
|   |-- report.py                    # HTML report generation with Plotly
|   |-- templates/
|       |-- dashboard.html           # Jinja2 template for the HTML dashboard
|-- gluecode/
|   |-- jira_csv_to_json.py          # Jira CSV -> Horizon JSON converter
|   |-- sample_data_gen.py           # Synthetic data generator
|-- tests/
|   |-- __init__.py
|   |-- test_models.py
|   |-- test_data_store.py
|   |-- test_simulation.py
|   |-- test_calendar_estimator.py
|   |-- test_reference_finder.py
|   |-- test_report.py
|   |-- test_cli.py
|   |-- fixtures/
|       |-- sample_team.json
|       |-- sample_jira_export.csv
|-- data/
    |-- example_team.json            # Shipped example
```

---

## CLI Commands

**Estimate:**
```
python main.py estimate --data data/team.json --name "Task name" --story-points 8 --estimate 5.0 --output report.html [--iterations 10000] [--sigma 2.5] [--seed 42]
```

**Import Jira CSV:**
```
python main.py import --csv export.csv --team "Team Alpha" --output data/team.json [--append]
```

**Validate data:**
```
python main.py validate --data data/team.json
```

---

## Tasks

### Task 1: Project Scaffolding and Dependencies
**Status:** DONE
**Description:** Create the `horizon/` package, `tests/`, `data/` directories. Write `requirements.txt` (numpy, pydantic, plotly, jinja2, pandas) and `requirements-dev.txt` (pytest, pytest-cov). Replace scaffold `main.py` with CLI entry point stub. Install all deps.
**Acceptance:** `python main.py` runs without error and prints a stub message.

---

### Task 2: Data Models (`horizon/models.py`)
**Status:** DONE
**Depends on:** Task 1
**Description:** Define Pydantic models: `Task` (id, name, story_points, estimated_days, actual_days, calendar_days, completed_date), `TeamData` (team name + task list), `EstimationRequest` (task_name, story_points, initial_estimate_days), `PercentileEstimate` (p10, p50, p90), `ReferenceCase` (task + similarity_score), `EstimationResult` (all results combined). Write unit tests for validation and JSON serialization round-trips.
**Acceptance:** All model tests pass.

---

### Task 3: Data Store (`horizon/data_store.py`)
**Status:** TODO
**Depends on:** Task 2
**Description:** Implement `load_team_data(path)`, `save_team_data(data, path)`, `merge_team_data(existing, new_tasks)`. Create `tests/fixtures/sample_team.json` with 10-15 realistic tasks. Test loading, saving, round-tripping, merge deduplication, and error cases (missing file, invalid schema).
**Acceptance:** All data_store tests pass.

---

### Task 4: Monte Carlo Simulation Engine (`horizon/simulation.py`)
**Status:** TODO
**Depends on:** Task 2
**Description:** Implement the core `run_estimation()` function and private helpers:
- `_compute_ratios()`: actual_days / estimated_days for each historical task
- `_compute_weights()`: Gaussian similarity `exp(-0.5 * ((sp_i - target) / sigma)^2)`, normalized
- `_bootstrap_sample()`: weighted sampling with replacement using numpy RNG
- `_extract_percentiles()`: P10, P50, P90 via numpy.percentile

Accept `seed` parameter for deterministic tests. Test: deterministic output, P10 < P50 < P90, convergence with single task, weight behavior at extreme sigma values.
**Acceptance:** All simulation tests pass. With fixed seed, output is reproducible.

---

### Task 5: Calendar Day Estimator (`horizon/calendar_estimator.py`)
**Status:** TODO
**Depends on:** Task 2
**Description:** Same weighted bootstrap approach as simulation.py but using `calendar_days / actual_days` ratios. Function `estimate_calendar_days()` returns `(PercentileEstimate, raw_samples)`. Test with deterministic seed, verify sanity constraints.
**Acceptance:** All calendar_estimator tests pass.

---

### Task 6: Reference Case Finder (`horizon/reference_finder.py`)
**Status:** TODO
**Depends on:** Task 2
**Description:** Implement `find_reference_cases()` — rank historical tasks by Gaussian similarity score on story points, normalize to [0,1], return top N. Test: exact match gets score 1.0, results sorted descending, handles edge cases.
**Acceptance:** All reference_finder tests pass.

---

### Task 7: Integration — Wire Simulation Pipeline
**Status:** TODO
**Depends on:** Tasks 4, 5, 6
**Description:** Update `simulation.run_estimation()` to call `calendar_estimator.estimate_calendar_days()` and `reference_finder.find_reference_cases()` internally, returning a fully populated `EstimationResult`. Add integration test loading fixture data and asserting all result fields are populated.
**Acceptance:** Integration test produces a complete `EstimationResult` with all fields sane.

---

### Task 8: HTML Report Generator (`horizon/report.py` + template)
**Status:** TODO
**Depends on:** Task 2
**Description:** Create Jinja2 template `horizon/templates/dashboard.html` and `report.py` with `generate_report(result)` and `save_report(html, path)`. Four dashboard sections:
1. **Refined Estimate:** Table (P10/P50/P90 effort-days) + Plotly histogram with vertical percentile lines
2. **Three-Point Estimation:** Table with Optimistic/Most Likely/Pessimistic + PERT weighted average `(P10 + 4*P50 + P90) / 6`
3. **Calendar Delivery:** Table (P10/P50/P90 calendar-days) + Plotly histogram
4. **Reference Cases:** HTML table with task details and similarity percentage

Use Plotly CDN for JS. Self-contained HTML output. Test: valid HTML, all sections present, Plotly divs embedded.
**Acceptance:** Generated HTML opens in browser and displays all four sections correctly.

---

### Task 9: CLI Implementation (`horizon/cli.py`)
**Status:** TODO
**Depends on:** Tasks 3, 7, 8
**Description:** Full argparse setup with `estimate`, `import` (stub initially), and `validate` subcommands. `cmd_estimate()` orchestrates: load data -> run estimation -> generate report -> print summary. `cmd_validate()` prints dataset stats. Test argument parsing and end-to-end estimate command with fixture data.
**Acceptance:** `python main.py estimate --data tests/fixtures/sample_team.json --name "Test" --story-points 5 --estimate 3.0 --output test_report.html` produces a valid HTML report.

---

### Task 10: Jira CSV Import Utility
**Status:** TODO
**Depends on:** Tasks 2, 3
**Description:** Create `gluecode/jira_csv_to_json.py` with configurable COLUMN_MAP at the top (standard Jira names: Issue key, Summary, Story Points, Original Estimate, Time Spent, Created, Resolved). Use pandas to read CSV, map columns. Compute `calendar_days` as `(Resolved - Created).days`. Convert Original Estimate and Time Spent from Jira's hours format to man-days (divide by 8). Handle missing values with warnings. Wire into `cli.py::cmd_import()`. Create test fixture CSV. Update GLUECODE.md.
**Acceptance:** `python main.py import --csv tests/fixtures/sample_jira_export.csv --team "Test" --output test_import.json` produces valid Horizon JSON.

---

### Task 11: Sample Data Generator
**Status:** TODO
**Depends on:** Task 2
**Description:** Create `gluecode/sample_data_gen.py`. Generate 50-100 tasks with Fibonacci story points, correlated estimates (0.5-1.5 days/SP), log-normal actuals (biased over estimate), calendar factor ~1.5x, dates spread over 12 months. Accept `--count`, `--team`, `--output` args. Update GLUECODE.md.
**Acceptance:** Generated JSON loads successfully and produces reasonable estimation results.

---

### Task 12: End-to-End Testing and Polish
**Status:** TODO
**Depends on:** All previous tasks
**Description:** Run full pipeline end-to-end: generate sample data -> estimate -> verify HTML report. Add `--verbose` flag for progress output. Add friendly error messages for edge cases (too few tasks, story points outside range). Verify all tests pass with `pytest --cov=horizon tests/`.
**Acceptance:** Full test suite passes. HTML report renders correctly in browser with all interactive elements working.

---

## Dependencies (requirements.txt)

| Package  | Version  | Purpose                                      |
|----------|----------|----------------------------------------------|
| numpy    | >=1.26   | Array operations, bootstrap sampling, percentiles |
| pydantic | >=2.5    | Data validation and JSON serialization       |
| plotly   | >=5.18   | Interactive charts in HTML reports           |
| jinja2   | >=3.1    | HTML template rendering                      |
| pandas   | >=2.1    | CSV reading for Jira import                  |

## Verification

1. `pip install -r requirements.txt -r requirements-dev.txt`
2. `python gluecode/sample_data_gen.py --count 75 --team "Demo Team" --output data/demo.json`
3. `python main.py validate --data data/demo.json`
4. `python main.py estimate --data data/demo.json --name "Build feature X" --story-points 5 --estimate 3.0 --output demo_report.html --seed 42`
5. Open `demo_report.html` in browser — verify all 4 sections render with interactive charts
6. `pytest --cov=horizon tests/` — all tests green
