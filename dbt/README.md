# dbt/

The data pipeline as dbt models: raw files in, a tested modeling table out. Run from the repo root:

```bash
pixi run build                                          # dbt deps + dbt build: every model, then its tests
pixi run dbt build --select mart_study__region_6h+      # one model and everything downstream
pixi run dbt build --select +mart_study__region_6h      # one model and everything upstream
pixi run dbt docs generate && pixi run dbt docs serve   # browsable docs + lineage graph
```

Writes to `data/warehouse.duckdb` in schemas `seeds`, `staging`, `intermediate`, `marts`.

## How a model works

- One `.sql` file = one table or view, named after the file. Just the `SELECT` — dbt writes the `CREATE`.
- Raw files: `{{ source('eaglei', 'outages') }}` (declared in `models/staging/_sources.yml`).
- Other models: `{{ ref('stg_eaglei__customers') }}` — this is how dbt knows the build order.
- Reusable SQL snippets: `macros/` — `{{ region_fips('fips_code') }}` (the St. Louis merge), `{{ block_6h('ts') }}`.
- Tests: in the `_*.yml` next to the models, or a SQL file in `tests/` that returns the *bad* rows.

## Layers

| Layer | Prefix | Materialized | Purpose |
|---|---|---|---|
| `seeds/` | — | table | small CSVs kept in git |
| `models/staging/` | `stg_<source>__<thing>` | view | one per raw source: rename, cast, decode — nothing else |
| `models/intermediate/` | `int_<area>__<thing>` | table | reshape and join |
| `models/marts/` | `mart_<area>__<thing>` | table | what the model and the app read |

## Models

| Model | What it is |
|---|---|
| `stg_eaglei__outages` | national 15-min snapshots; 2023 `sum` merged; `snapshot_time` on the 15-min grid |
| `stg_eaglei__customers` | customers per county (MCC.csv), FIPS zero-padded |
| `stg_hrrr__hourly` | HRRR ingredients per region per hour, with u/v wind components |
| `stg_noaa__storm_events` | MO + IL storm reports, times converted to UTC |
| `stg_noaa__zone_county` | NWS forecast zone → county |
| `stg_acs__housing` | housing age, units, population per county |
| `stg_geo__regions` | 216 regions with land area, weather point, tree canopy |
| `stg_noaa__kstl_hourly` | KSTL airport hourly weather (used by the legacy St. Louis notebook) |
| `int_study__regions` | one row per region with every place feature |
| `int_eaglei__blocks_6h` | every 6-hour block + national snapshot count (the heartbeat) |
| `int_study__outages_6h` | peak / mean customers out per region per block |
| `int_study__weather_6h` | storm ingredients per region per block |
| `int_study__storm_events_6h` | storm report counts per region per block |
| `mart_study__region_6h` | **the modeling table**: region x block, label + features + context (3.5M rows) |
| `mart_study__region_resilience` | **the scorecard**: 2020–2023 outage burden, events/yr, storm hit rate, repeats |

The St. Louis hourly prototype (KSTL weather, hourly grid) is in `../legacy/`.
