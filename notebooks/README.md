# notebooks/

Use the pixi kernel (`.pixi/envs/default/bin/python`). Both notebooks open the warehouse
read-only — close them (or restart the kernel) before `pixi run build`.

| Notebook | For |
|---|---|
| `01_raw_data.ipynb` | Every source in `data/raw/`, read from the files before dbt: EAGLE-I columns, heartbeat and one county's snapshots; HRRR hourly and forecasts as issued (successive runs); NWS warnings, SPC outlooks, Storm Events; canopy, place and ACS maps. Doesn't touch the warehouse. |
| `02_warehouse.ipynb` | The whole-country warehouse: every table, dbt lineage and test results, heartbeat and coverage, one county through a storm hour by hour, the label built with `ml/data.py`'s own query, base rates, what warnings and outlooks already tell you, neighbours, history. Read-only: run its last cell before `pixi run build`. |
| `03_experiments_models.ipynb` | Pipeline steps and whether each is stale, logs, `summary.md`, the results ladder, significance, the E55 ablations, E57a, state by state, the audit, every result file, MLflow runs, the saved XGBoost models (gain importance, a tree), and the 2025 predictions (PR curves, calibration, alerts, by month). |
| `explore_warehouse.ipynb` | Look at any table: list with row counts, columns + preview, one region through a storm, biggest outage blocks, raw EAGLE-I snapshots for a county, feature distributions, a map. `q("SELECT ...")` runs any SQL. |
| `benchmark_lab.ipynb` | Try configs interactively with the benchmark's own code: write a config as a dict, run it, compare, open up one model (precision–recall, calibration, importance, misses), then save it as `ml/benchmarks/<name>.yaml` for a logged run. |
