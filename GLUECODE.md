# Gluecode Registry

## gluecode/sample_data_gen.py

Generate synthetic historical task data for testing and demos.

```
python gluecode/sample_data_gen.py --count 75 --team "Demo Team" --output data/demo.json --seed 0
```

Arguments:
- `--count` — number of tasks (default: 75)
- `--team` — team name (default: "Demo Team")
- `--output` — output JSON path (default: data/demo.json)
- `--seed` — RNG seed for reproducibility (default: 0)
