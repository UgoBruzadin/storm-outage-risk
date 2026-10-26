# legacy/

The first version of the pipeline: plain SQL files run in order by a small
Python script, before the move to dbt. Kept because
`model_playground.ipynb` (St. Louis metro, hourly) reads its tables.

- `sql/merge_all.sql` — 7 St. Louis-area regions × every hour, outages +
  KSTL airport weather → `stg.merged_hourly`
- `sql/build_mo_il.sql` — sparse hourly outages for all MO + IL regions
- `build_warehouse.py` — runs both: `pixi run build-legacy`

The current pipeline is in `dbt/` (`pixi run build`).
