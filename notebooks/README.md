# notebooks/

Use the pixi kernel (`.pixi/envs/default/bin/python`). Both notebooks open the warehouse
read-only — close them (or restart the kernel) before `pixi run build`.

| Notebook | For |
|---|---|
| `explore_warehouse.ipynb` | Look at any table: list with row counts, columns + preview, one region through a storm, biggest outage blocks, raw EAGLE-I snapshots for a county, feature distributions, a map. `q("SELECT ...")` runs any SQL. |
| `benchmark_lab.ipynb` | Try configs interactively with the benchmark's own code: write a config as a dict, run it, compare, open up one model (precision–recall, calibration, importance, misses), then save it as `ml/benchmarks/<name>.yaml` for a logged run. |
