# ml/ — the benchmark suite

Compare models, hyperparameters and feature sets on equal terms: same data, same
splits, same metrics, every run logged.

```bash
pixi run benchmark ml/benchmarks/quick.yaml --dry-run   # list the runs it would do
pixi run train                                          # = the quick benchmark (minutes)
pixi run benchmark ml/benchmarks/full.yaml              # grid search + canopy ablation (~30–60 min)
pixi run benchmark ml/benchmarks/full.yaml --models lightgbm   # just one family
pixi run mlflow-ui                                      # browse/compare runs: http://127.0.0.1:5000
pixi run export-app [--config ml/benchmarks/full.yaml]  # train the config's `final:` model for the dashboard
```

Each benchmark writes `results/benchmark_<name>.csv` (every run) and
`results/leaderboard_<name>.md` (ranked, per split) — both committed, so results are part
of the history — and logs every run to MLflow (experiment `benchmark/<name>`, tagged with
the git commit).

## Pieces

| File | What it holds | Change it to… |
|---|---|---|
| `benchmarks/*.yaml` | what to compare | run a new experiment — copy `quick.yaml` |
| `data.py` | loading + **feature groups** (`weather`, `place`, `canopy`, `history`, `recent`) | add a feature (compute it in dbt, list it in a group) |
| `models.py` | **model registry** + baselines (`prior`, `climatology`) | add a model family (one builder function) |
| `splits.py` | `time`, `county`, `random` | add a validation scheme |
| `metrics.py` | PR-AUC, lift, ROC-AUC, Brier, log loss, precision/recall in the top 1% | add a metric |
| `benchmark.py` | expands the config into runs, evaluates, logs, ranks | — |
| `export_app_data.py` | trains `final:` and exports the dashboard's files | — |

## Writing a config

```yaml
name: my-idea                     # -> results/benchmark_my-idea.csv
data: {threshold_pct: 5, years: [2024, 2025]}
splits:
  - {kind: time, train_years: [2024], test_years: [2025]}
  - {kind: county, folds: 5}
features: [weather, weather+place-canopy]      # "+" adds a group, "-" removes one
models:
  - name: climatology                          # baselines ignore `features`
  - name: lightgbm
    params: {num_leaves: [15, 63], learning_rate: 0.03}   # a list = try each value (grid)
final: {model: lightgbm, params: {num_leaves: 15}, features: weather+place}
```

## Reading results

- **PR-AUC** is the headline. Events are rare (~1% of blocks), so "no skill" scores the
  event rate, not 0.5 — that's why **lift** (PR-AUC ÷ event rate) is shown too.
- Always look at the **baselines** first. A model that can't beat `climatology` (each
  region's usual rate by month, no weather) hasn't learned anything about storms.
- **`time`** = predicting a future year; **`county`** = predicting places the model never
  saw; **`random`** = random region-days, optimistic because one storm lands on both sides.
- Change one thing per comparison. MLflow's compare view (select runs → Compare) shows
  which parameter moved the score.
