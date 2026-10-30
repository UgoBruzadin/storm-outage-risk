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
| `value.py` | what acting on each forecast was worth in the test year: relative economic value and dollar scenarios | change the scenarios (`MIXES`, `RESTORATION_CUT`, `STAGING_COST`) |
| `lead_time.py` | 6-hour blocks with weather from before the block only, at several leads | — |
| `moving_window.py` | the main benchmark: a decision every hour about the 6 hours starting 0–6 h later, every input known by then | change `FEATURES` or `RUNS` |
| `hourly_ablation.py`, `hourly_tune.py` | feature and settings decisions for the moving-window model, on 2024, over seeds | change `CONFIGS` or `GRID` |
| `value_hourly.py` | `value.py` for the moving-window model, staging crews on alert episodes | — |
| `forecast_test.py` | the moving-window model with HRRR forecasts of the window it predicts, with storm-day ranges | change `LEAD` or `RUN_AGE` |
| `forecast_ensemble.py` | a probability range per decision from the HRRR runs issued 2–6 h before | change `RUN_AGES` |
| `uncertainty.py` | paired bootstrap over storm days: 95% ranges for scores and differences | change `N_RESAMPLES` |
| `significance.py` | paired tests between models: storm-day bootstrap and permutation p-values | change `COMPARISONS` |
| `canopy_by_state.py` | does canopy help the model in Missouri, Illinois or both | — |
| `audit.py` | checks for look-ahead, clock and leakage problems (docs/audit.md) | — |
| `export_hourly.py` | the hourly results the site and dashboard read | change `HEADLINE` or `SHARES` |

Every experiment, its result and what it means: [docs/experiments.md](../docs/experiments.md).

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
