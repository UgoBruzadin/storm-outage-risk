# Data dictionary

Every table, every model feature, and the SQL techniques that build them. Row counts are
from the last `pixi run build` (HRRR counts grow as more weather years download).

```
raw files ──► staging (views)          ──► intermediate (tables)            ──► marts (tables)              ──► ml/
EAGLE-I       stg_eaglei__outages          int_eaglei__blocks_6h (heartbeat)    mart_mo_il__region_6h           features + label
MCC.csv       stg_eaglei__customers        int_mo_il__regions                   mart_mo_il__region_resilience
HRRR          stg_hrrr__hourly             int_mo_il__outages_6h
Storm Events  stg_noaa__storm_events       int_mo_il__weather_6h
zone file     stg_noaa__zone_county        int_mo_il__storm_events_6h
ACS           stg_acs__housing
geo + canopy  stg_geo__regions
KSTL          stg_noaa__kstl_hourly        (legacy St. Louis notebook only)
```

Two ideas run through everything:
- **Region** = a county, except St. Louis City (29510) + County (29189), merged into
  `29189+29510` because EAGLE-I files the County's outages under the City in 2020–2024.
  216 regions. Macro: `{{ region_fips('col') }}`.
- **Block** = 6 hours starting 00/06/12/18 UTC. Macro: `{{ block_6h('col') }}`.

---

## Staging — one view per raw source (rename, cast, decode; nothing else)

| Table | One row = | Rows | What it does |
|---|---|---|---|
| `stg_eaglei__outages` | county × 15-min snapshot with ≥ 1 customer out (all U.S.) | view over ~250M | merges 2023's `sum` column into `customers_out`; adds `snapshot_time` (rounded to 15 min — Sept 2025 has duplicate snapshots) |
| `stg_eaglei__customers` | county | 3,233 | customers per county; FIPS zero-padded; drops `Grand Total` |
| `stg_hrrr__hourly` | region × hour | 5.1M | HRRR storm ingredients; converts wind speed + direction to u/v components so shear can be computed |
| `stg_noaa__storm_events` | storm report (MO + IL) | 48,450 | rebuilds timestamps, converts local standard time → UTC |
| `stg_noaa__zone_county` | NWS zone × county | 221 | maps winter-storm zones to counties |
| `stg_acs__housing` | county (MO + IL) | 217 | population, housing units, homes built before 1960, median year built |
| `stg_geo__regions` | region | 216 | land area, weather point (lat/lon), tree canopy |
| `stg_noaa__kstl_hourly` | hour | 102,035 | airport weather; legacy notebook only |

## Intermediate — reshape and join

| Table | One row = | Rows | Built how |
|---|---|---|---|
| `int_mo_il__regions` | region | 216 | customers summed per region; ACS joined; density = housing ÷ land km² |
| `int_eaglei__blocks_6h` | 6-hour block | 16,316 | **heartbeat**: how many national snapshots exist in the block (max 24). `eaglei_ok` = at least 12 → EAGLE-I was running |
| `int_mo_il__outages_6h` | region × block *with an outage* | 1.33M | per county per slot (max) → **sum** counties into regions per slot → per block: `peak_out` (max), `mean_out` (avg, missing slots = 0) |
| `int_mo_il__weather_6h` | region × block | 632k | HRRR hours summarized per block (max wind, total rain, …) |
| `int_mo_il__storm_events_6h` | region × block with a report | 254k | report counts by type; zone events spread to their counties; multi-block events counted in each block |

## Marts — what the model and the app read

### `mart_mo_il__region_6h` — the modeling table (3.52M rows = 216 regions × 16,316 blocks)

Built as a **grid**: every region `CROSS JOIN` every block, then `LEFT JOIN` outages,
weather and storm reports, so blocks with no outage exist (as 0) instead of being missing.

| Column | Meaning |
|---|---|
| `peak_out` | worst customers-out snapshot in the block. **NULL** if EAGLE-I was down; **0** if it was up and the region had no row; else the value |
| `peak_suspect` | peak > 1.5 × customers (a glitch, or a customer count that's too low) |
| `peak_pct_out` | peak ÷ customers × 100, capped at 100; NULL if unknown or suspect — **the label comes from this** |
| `mean_out` | average customers out over the block |
| `eaglei_snapshots` | heartbeat count for the block |
| `has_weather` | all 6 hours of HRRR weather exist |
| weather, place, calendar columns | see Features below |
| `storm_*` | NOAA storm report counts — **context only, never features** (written after the fact) |

### `mart_mo_il__region_resilience` — the scorecard (216 rows)

From **2020–2023 only** (dbt vars `history_start` / `history_end`), so it can be used as
features for 2024–2025 without leaking. An **event** = consecutive blocks with ≥ 1% out.

| Column | Meaning |
|---|---|
| `hours_out_per_customer` | customer-hours lost ÷ customers ÷ years (a SAIDI-like burden) |
| `events_per_year` | events per year |
| `storm_hit_rate` | share of blocks with a storm report that became an event — closest to "vulnerability" |
| `quiet_event_rate` | share of blocks *without* a storm report that became an event |
| `median_event_hours` | typical event length (6-hour resolution — too coarse to be useful yet) |
| `repeat_7d_share` | share of events followed by another within 7 days |

---

## Features — what the model sees (groups in `ml/data.py`)

Rule for every feature: **would I know this at the start of the block?**

### `weather` — HRRR storm ingredients for the block (≈ weathernext)

| Feature | Definition | Why it matters |
|---|---|---|
| `gust_max_ms` | max 10 m wind gust, m/s | damaging wind at the surface |
| `wind10_max_ms` | max sustained 10 m wind | — |
| `wind850_max_ms` | max wind at 850 hPa (~1.5 km) | low-level jet; can mix down in storms |
| `shear_0_6km_max_ms` | max \|wind at 500 hPa − wind at 10 m\| | organized, severe storms need shear |
| `cape_max_jkg` | max CAPE, J/kg | energy for updrafts (storm strength) |
| `precip_sum_mm`, `precip_max_1h_mm` | total / heaviest hourly rain | saturated soil + wind topples trees |
| `temp_min_c`, `temp_mean_c` | 2 m temperature | cold + wet = ice |
| `freezing_level_min_m` | lowest freezing level | low + unstable = hail |
| `icing_hours` | hours with temp ≤ 0 °C and precipitation | ice on lines and limbs |
| `hail_hours` | hours with CAPE ≥ 500, rain ≥ 2 mm, freezing level ≤ 3.5 km | crude hail proxy |
| `wind_x_precip`, `wind_squared`, `shear_x_cape` | interactions (from weathernext) | wind load grows ~ with speed² |
| `month`, `block_hour_utc` | calendar | seasons, time of day |

**Caveat:** HRRR via Open-Meteo is close to observed weather (each run's first hours), so
this is an upper bound for a 24–48 h forecast.

### `place` — fixed per region

| Feature | Definition |
|---|---|
| `log_customers` | log10 of customers (MCC) |
| `housing_per_km2` | housing units ÷ land area |
| `share_homes_pre1960` | homes built before 1960 ÷ all homes (older area ≈ older trees and lines) |
| `median_year_built` | ACS median year built |
| `canopy_mean_pct` | average tree canopy % (USFS/NLCD 2021) |
| `canopy_dense_share` | share of land with ≥ 50% canopy |

`canopy` = the two canopy features, used for ablations (`weather+place-canopy`).

### `history` — the region's 2020–2023 track record

`hist_hours_out_per_customer`, `hist_events_per_year`, `hist_storm_hit_rate`,
`hist_quiet_event_rate`, `hist_repeat_7d_share` — the scorecard columns above.

### `recent` — outages already known at the block's start

| Feature | Definition |
|---|---|
| `prev_block_pct_out` | `peak_pct_out` of the previous block (`lag`) |
| `max_pct_out_prev_24h` | max `peak_pct_out` over the previous 4 blocks (window `4 PRECEDING AND 1 PRECEDING`) |

Computed on the full grid **before** filtering years, so a year's first block still sees
the previous year.

### Label and evaluation columns (added in `ml/data.py`, not in dbt)

| Column | Meaning |
|---|---|
| `y` | `peak_pct_out ≥ threshold` (1, 5 or 10) |
| `is_onset` | previous block known and **below** the threshold → a *new* outage. Rows with an unknown previous block are neither |

---

## SQL techniques — what we used and where

| Technique | What it does | Where |
|---|---|---|
| `read_csv(..., union_by_name = true)` | stack files whose columns differ, matching by name | `_sources.yml` (EAGLE-I, HRRR, Storm Events) |
| `coalesce(a, b)` | first non-NULL value | 2023's `sum` column; storm counts → 0 |
| `{{ source() }}` / `{{ ref() }}` | dbt: read a raw file / another model; builds the dependency graph | every model |
| macros | reusable SQL snippets | `region_fips`, `block_6h` |
| `time_bucket` / `date_trunc` | round timestamps down | 15-min slots; 6-hour blocks |
| `GROUP BY ALL` + `max`/`sum`/`avg` | aggregate snapshots into blocks | `int_mo_il__outages_6h`, `int_mo_il__weather_6h` |
| `count(*) FILTER (WHERE …)` | conditional counts in one pass | weather hours, storm types, scorecard rates |
| `CROSS JOIN` + `LEFT JOIN` | full grid, then attach what exists (missing → NULL) | `mart_mo_il__region_6h` |
| three-way `CASE` | NULL (unknown) vs 0 (none) vs value | `peak_out` |
| heartbeat | judge coverage from the whole country | `int_eaglei__blocks_6h` |
| `generate_series` + `unnest` | make every block / spread a storm over the blocks it spans | blocks, storm events |
| `UNION ALL BY NAME` | stack county and zone events | `int_mo_il__storm_events_6h` |
| window functions `lag`, `lead`, `max … ROWS BETWEEN` | look at neighboring blocks per region | `recent` features, scorecard |
| gaps-and-islands (`lag` + running `sum` of start flags) | group consecutive event blocks into events | `mart_mo_il__region_resilience` |
| `QUALIFY row_number() … = 1` | keep one row per group (filter on a window) | KSTL duplicate reports |
| `arg_max(x, y)` | the x from the row with the largest y | latest county name (legacy MO/IL build) |
| `regexp_matches` | pattern search in text | thunder in METAR (KSTL) |
| `* EXCLUDE (…)` / `* REPLACE (…)` | select all columns but drop / rewrite some | legacy loads |
| singular dbt tests | a query that returns the *bad* rows | `dbt/tests/*.sql` |

**NULL traps to remember:** `least()` / `greatest()` skip NULLs (`least(100, NULL)` = 100);
`WHERE` runs before window functions (filter after computing lags); `count(col)` skips
NULLs while `count(*)` doesn't.
