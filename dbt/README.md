# dbt/

The SQL pipeline as dbt models. Run everything from the repo root:

```bash
pixi run dbt build                         # seeds + models + tests, in dependency order
pixi run dbt build --select stg_eaglei__customers   # just one model (+ its tests)
pixi run dbt build --select +mart_stl__hourly        # a model and everything upstream of it
pixi run dbt docs generate && pixi run dbt docs serve   # browsable docs + lineage graph
```

Writes to `data/warehouse.duckdb` (schemas `seeds`, `staging`, `intermediate`, `marts`).

## How a model works

- One `.sql` file = one table or view, named after the file. Just the `SELECT` — no `CREATE TABLE`.
- Read raw files with `{{ source('eaglei', 'outages') }}` (declared in `models/staging/_sources.yml`).
- Read other models with `{{ ref('stg_eaglei__customers') }}` — this is how dbt learns the order to build things.
- Tests live in the `_*.yml` file next to the models (`unique`, `not_null`, …) or as SQL in `tests/` that returns the *bad* rows.

## Naming

| Layer | Prefix | Materialized | Purpose |
|---|---|---|---|
| `seeds/` | — | table | small CSVs kept in git (`stl_metro_counties`) |
| `models/staging/` | `stg_<source>__<thing>` | view | one per raw source: rename, fix types/codes, nothing else |
| `models/intermediate/` | `int_<area>__<thing>` | table | reshape and join: hourly tables, regions, grid, heartbeat |
| `models/marts/` | `mart_<area>__<thing>` | table | what the model and the app read |

## Model plan (milestone 1)

Where each piece of the old `sql/merge_all.sql` goes, and its check number.

| # | Model | From old section | Check |
|---|---|---|---|
| ✅ | `stg_noaa__kstl_hourly` | 2 + 3 | 102,035 rows, `hour` unique |
| 1 | `stg_eaglei__customers` | 5 (MCC part) | 3,233 rows, `fips_code` unique |
| 2 | `stg_eaglei__outages` | 1 (no county filter: national) | `not_null` on keys |
| 3 | `int_eaglei__heartbeat` | 5 (snapshots) | 97,536 rows, `hour` unique |
| 4 | `int_stl__county_regions` | 4 (`stg.regions`) | 8 rows |
| 5 | `int_stl__regions` | 5 (`stg.counties`) | 7 rows, Monroe = 15,588 customers |
| 6 | `int_stl__outage_hourly` | 4 (`stg.outage_hourly`) | 364,944 rows, (`fips_code`, `hour`) unique |
| 7 | `int_stl__hours` | 5 (`stg.hours`) | 94,850 rows |
| 8 | `mart_stl__hourly` | 6 | 663,950 = 343,735 outage + 313,942 quiet + 6,273 unknown |

`sql/build_mo_il.sql` moves into dbt in milestone 2, reusing models 1–3.
