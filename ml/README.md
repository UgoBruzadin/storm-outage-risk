# ml/

- `train.py` (`pixi run train`) — evaluates every feature set x split x model on
  `marts.mart_mo_il__region_6h`, logs each run to MLflow (`pixi run mlflow-ui`) and writes
  `results/summary_ge<threshold>pct.csv` (tracked in git).
- `export_app_data.py` (`pixi run export-app`) — trains the final model (2024 → predicts 2025)
  and writes the small Parquet files the dashboard reads to `../data/app/`.

Feature sets: `weather` (weathernext's ingredients), `+place` (canopy, housing age, density,
size), `-canopy` (ablation), `+history` (2020–2023 resilience). Splits: `time`, `county`
(held-out regions), `random` (weathernext-style, optimistic on purpose).
