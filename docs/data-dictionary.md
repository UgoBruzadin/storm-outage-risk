# Data dictionary

Every table, every model feature, and the SQL techniques that build them. Row counts are
from the last `pixi run build` (HRRR counts grow as more weather years download).

```
raw files ──► staging (views)          ──► intermediate (tables)            ──► marts (tables)              ──► ml/
EAGLE-I       stg_eaglei__outages          int_eaglei__blocks_6h (heartbeat)    mart_study__region_6h           features + label
MCC.csv       stg_eaglei__customers        int_study__regions                   mart_study__region_resilience
HRRR          stg_hrrr__hourly             int_study__outages_6h
Storm Events  stg_noaa__storm_events       int_study__weather_6h
zone file     stg_noaa__zone_county        int_study__storm_events_6h
ACS           stg_acs__housing
geo + canopy  stg_geo__regions
KSTL          stg_noaa__kstl_hourly        (legacy St. Louis notebook only)
```

## Where the data comes from

Every raw file, who publishes it, and how it gets here. All public and free; everything
except EAGLE-I is downloaded by a script (`pixi run fetch-<name>`, code in `ingest/`).

| Data | Publisher | What it is | Years / version | Source (URL) | How we get it | Lands in |
|---|---|---|---|---|---|---|
| **Power outages** | U.S. DOE / Oak Ridge National Laboratory (EAGLE-I) | customers out per county every 15 min, scraped from utility outage maps | 2014-11 → 2025 | figshare / ORNL releases — cite DOI [10.13139/ORNLNCCS/1975202](https://doi.org/10.13139/ORNLNCCS/1975202) (data) and [10.13139/ORNLNCCS/1975203](https://doi.org/10.13139/ORNLNCCS/1975203) (documentation); `citation_*.txt` ship with the download | **manual download** (one zip per release) | `data/raw/eaglei/eaglei_outages_*.csv` |
| Customers per county | same (EAGLE-I) | modeled customer count per county (`MCC.csv`) and state coverage over time (`coverage_history.csv`) | ships with the outage data | same download | manual | `data/raw/eaglei/` |
| **Storm ingredients** | NOAA (HRRR model), served by **Open-Meteo** | hourly wind, gusts, winds aloft, CAPE, precipitation, temperature, freezing level at each region's weather point | 2018–2025 (HRRR archive begins 2018-01-01) | `https://historical-forecast-api.open-meteo.com/v1/forecast` with `models=ncep_hrrr_conus` | `fetch-weather` (rate-limited, resumable) | `data/raw/weather/hrrr/<region>_<year>.csv.gz` |
| **Storm reports** | NOAA NCEI Storm Events database | spotter / NWS reports of thunderstorm wind, hail, tornadoes, winter storms… with times and places | 2014–2025 | `https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` | `fetch-storm-events` (newest file per year) | `data/raw/storm_events/` |
| **Official forecasts** | NWS warnings and SPC Day 1 convective outlooks, archived by the Iowa Environmental Mesonet | warnings (severe thunderstorm, tornado, high wind, ice storm, winter storm, blizzard) by county or zone, with issue and expiry; outlook polygons (risk level, wind / tornado / hail probability) joined to each region's interior point | 2014–2025 | `https://mesonet.agron.iastate.edu/cgi-bin/request/gis/` (`watchwarn.py`, `outlooks.py`) | `fetch-nws` | `data/raw/nws/` |
| Zone → county map | NOAA National Weather Service | which counties make up each forecast zone | file `bp16ap26` (16 Apr 2026) | `https://www.weather.gov/gis/ZoneCounty` | `fetch-storm-events` | `data/raw/storm_events/zone_county_*.dbx` |
| **County shapes** | U.S. Census Bureau (TIGER cartographic boundaries) | county polygons and land area, 1:500k | 2023 | `https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip` | `fetch-counties` | `data/raw/geo/regions_study.*` |
| **Tree canopy** | USDA Forest Service, distributed by MRLC (NLCD Tree Canopy Cover) | % tree canopy per 30 m pixel; we request 90 m | 2021 (v2021-4) | MRLC map service `https://www.mrlc.gov/geoserver/ows`, coverage `mrlc_download__nlcd_tcc_conus_2021_v2021-4` | `fetch-tree-canopy` (one cut-out per region, summarized) | `data/raw/geo/tree_canopy_2021.csv` |
| **Housing** | U.S. Census Bureau, American Community Survey | tables B25034 (year built), B25035 (median year built), B01003 (population), B25001 (housing units) | 2020–2024 5-year estimates | `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/` (the Census API now needs a key; these files don't) | `fetch-acs` | `data/raw/acs/` |
| Airport weather (legacy) | NOAA NCEI Global Hourly (ISD), AWS Open Data mirror | observations at St. Louis Lambert (KSTL, station 72434013994) | 2014–2025-08 | `https://noaa-global-hourly-pds.s3.amazonaws.com/<year>/72434013994.csv` | `fetch-noaa` | `data/raw/noaa/` |

Each source's quirks, and what we did about them, are in [data-notes.md](data-notes.md).

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
| `int_study__regions` | region | 216 | customers summed per region; ACS joined; density = housing ÷ land km² |
| `int_eaglei__blocks_6h` | 6-hour block | 16,316 | **heartbeat**: how many national snapshots exist in the block (max 24). `eaglei_ok` = at least 12 → EAGLE-I was running |
| `int_study__outages_6h` | region × block *with an outage* | 1.33M | per county per slot (max) → **sum** counties into regions per slot → per block: `peak_out` (max), `mean_out` (avg, missing slots = 0) |
| `int_study__weather_6h` | region × block | 632k | HRRR hours summarized per block (max wind, total rain, …) |
| `int_study__storm_events_6h` | region × block with a report | 254k | report counts by type; zone events spread to their counties; multi-block events counted in each block |

## Marts — what the model and the app read

### `mart_study__region_6h` — the modeling table (3.52M rows = 216 regions × 16,316 blocks)

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

### `mart_study__region_resilience` — the scorecard (216 rows)

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

### `weather` — HRRR storm ingredients for the block

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
| `wind_x_precip`, `wind_squared`, `shear_x_cape` | interactions | wind load grows ~ with speed² |
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

### `warnings` and `outlook` — official forecasts (`int_study__nws_6h`)

| Feature | Definition |
|---|---|
| `warn_svr`, `warn_tor`, `warn_wind`, `warn_winter` | an NWS severe thunderstorm / tornado / high wind / winter (ice storm, winter storm, blizzard) warning was in force at any time in the block; zone warnings spread to every county in the zone |
| `spc_cat` | SPC Day 1 categorical risk at the region's interior point: 0 none, 1 TSTM, 2 MRGL, 3 SLGT, 4 ENH, 5 MDT, 6 HIGH |
| `spc_wind_prob`, `spc_tor_prob`, `spc_hail_prob` | that outlook's probability of the hazard within 25 miles |

The outlook is the latest product issued **before** the block starts and valid at its start
(`spc_lead_hours` > 0, tested). Warnings are often issued during the block. Used as features
and as the `nws_warnings`, `spc_outlook` and `official` baselines (`ml/models.py`).

### Label and evaluation columns (added in `ml/data.py`, not in dbt)

| Column | Meaning |
|---|---|
| `y` | `peak_pct_out ≥ threshold` (1, 5 or 10) |
| `is_onset` | previous block known and **below** the threshold → a *new* outage. Rows with an unknown previous block are neither |

---

## How the models are evaluated

### The two validation splits — and why both

A model is only as good as the test that judges it, and there are two different
questions a user of this model would ask. Each split answers one:

| Split | Train on | Test on | Question it answers | Why it's set up this way |
|---|---|---|---|---|
| **time** | all of 2024 | all of 2025 | "Trained on the past, does it work next year?" — how it would be used for real | The only years with HRRR weather downloaded so far. The test year is entirely after the training year, so no storm appears in both. Weakness: one year of storms is a small sample — a quiet or wild 2025 moves the score. More years (2020–2023, downloading) will allow 2020–2023 → 2024–2025 |
| **county**, 5 folds | 80% of the regions (2024 + 2025) | the other 20% | "Does it work for a place it has never seen?" — the honest test for *place* features (canopy, housing age) | Regions are split into 5 groups (~43 each). Each group is held out once while the model trains on the other 4, so **every region gets tested exactly once**, by a model that never saw it — all 216 regions contribute to the score, not just one random 20%. 5 is the usual trade-off: each model still trains on 80% of the data, and 5 fits per run keep it fast. More folds = more training data per fit but slower; fewer = noisier |

They answer different questions, so they can disagree — and that's informative:
place features help more on `county` (they're how the model tells an unseen place apart)
than on `time` (where the model already knows every region from training).

A third split, **random** (5 folds by region-day hash), is included for comparison with random-day evaluations such as weathernext-outage-forecasting. One storm hits
neighboring counties on the same day, so it lands on both sides of the split and scores
come out optimistic. It's in the code to *demonstrate* that, not to choose models.

Predictions from all folds are pooled and scored once, so `county` produces one number,
not five. (There are no confidence intervals yet — a bootstrap over storm days is on the
roadmap; until then, treat differences under ~0.005 PR-AUC as possibly noise.)

### Benchmark configs — what each one compares (`ml/benchmarks/`)

| Config | Question | Runs | What varies | Fixed |
|---|---|---|---|---|
| `quick.yaml` | Which **model family** is best, and do features beyond weather help? | 66 | models: prior, climatology, logistic, LightGBM, XGBoost (one setting each); features: weather → +place+history → +recent; outage size 1/5/10% | trained on all blocks |
| `onsets.yaml` | Should a model of **new outages** be **trained** on new outages only? And does **canopy** help? | 72 | `train_on`: all vs onsets; features incl. `weather+place` vs `weather+place-canopy`; outage size 1/5/10% | LightGBM only (+ climatology baseline) |
| `official.yaml` | Does the model beat, and add to, **NWS warnings and SPC outlooks**? | 54 | baselines: climatology, nws_warnings, spc_outlook, official; XGBoost on official forecasts only, on the model's features, and on both; outage size 1/5/10% | final XGBoost settings |
| `weathernext.yaml` | How does **weathernext-outage-forecasting's setup** score on this data, under its split and under ours? | 9 | splits: random (theirs), county, time; their features, class-weighted boosted tree and logistic regression vs the final model | ≥ 5% |
| `splits.yaml` | How much does the **choice of test set** change the score? | 9 | splits: time, county, random | final XGBoost settings, ≥ 5% |
| `wet_soil.yaml` | Does **rain before the block** help? | 64 | `wet_soil` group on/off, LightGBM and XGBoost, train on all vs onsets; outage size 5/10% | — |
| `full.yaml` | What are the **best hyperparameters**? | 264 | grids: LightGBM (trees, learning rate, leaves, class weight), XGBoost (trees, depth, min child weight, class weight), HGB; plus the canopy ablation; outage size 1/5/10% | trained on all blocks |

All configs use the same data, splits and metrics, and **every run is scored twice**: on all
blocks, and on **new outages** (blocks whose previous 6 hours weren't already an event) —
leaderboards rank by the second. `train_on` is about which rows the model *learns* from;
the onset *score* is computed for every run either way.

Results: `ml/results/benchmark_<config>.csv` (every number) and
`ml/results/leaderboard_<config>.md` (ranked). Metrics are defined in `ml/metrics.py`.

---

## SQL techniques — what we used and where

| Technique | What it does | Where |
|---|---|---|
| `read_csv(..., union_by_name = true)` | stack files whose columns differ, matching by name | `_sources.yml` (EAGLE-I, HRRR, Storm Events) |
| `coalesce(a, b)` | first non-NULL value | 2023's `sum` column; storm counts → 0 |
| `{{ source() }}` / `{{ ref() }}` | dbt: read a raw file / another model; builds the dependency graph | every model |
| macros | reusable SQL snippets | `region_fips`, `block_6h` |
| `time_bucket` / `date_trunc` | round timestamps down | 15-min slots; 6-hour blocks |
| `GROUP BY ALL` + `max`/`sum`/`avg` | aggregate snapshots into blocks | `int_study__outages_6h`, `int_study__weather_6h` |
| `count(*) FILTER (WHERE …)` | conditional counts in one pass | weather hours, storm types, scorecard rates |
| `CROSS JOIN` + `LEFT JOIN` | full grid, then attach what exists (missing → NULL) | `mart_study__region_6h` |
| three-way `CASE` | NULL (unknown) vs 0 (none) vs value | `peak_out` |
| heartbeat | judge coverage from the whole country | `int_eaglei__blocks_6h` |
| `generate_series` + `unnest` | make every block / spread a storm over the blocks it spans | blocks, storm events |
| `UNION ALL BY NAME` | stack county and zone events | `int_study__storm_events_6h` |
| window functions `lag`, `lead`, `max … ROWS BETWEEN` | look at neighboring blocks per region | `recent` features, scorecard |
| gaps-and-islands (`lag` + running `sum` of start flags) | group consecutive event blocks into events | `mart_study__region_resilience` |
| `QUALIFY row_number() … = 1` | keep one row per group (filter on a window) | KSTL duplicate reports |
| `arg_max(x, y)` | the x from the row with the largest y | latest county name (legacy MO/IL build) |
| `regexp_matches` | pattern search in text | thunder in METAR (KSTL) |
| `* EXCLUDE (…)` / `* REPLACE (…)` | select all columns but drop / rewrite some | legacy loads |
| singular dbt tests | a query that returns the *bad* rows | `dbt/tests/*.sql` |

**NULL traps to remember:** `least()` / `greatest()` skip NULLs (`least(100, NULL)` = 100);
`WHERE` runs before window functions (filter after computing lags); `count(col)` skips
NULLs while `count(*)` doesn't.
