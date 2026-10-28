# ⚡ Storm Outage Risk — Missouri & Illinois

> Which counties lose power when a storm hits — and why does the same storm hit some places much harder than others?

A county-level power-outage model for the 216 counties of Missouri and Illinois, built on
public data: DOE EAGLE-I outage records, NOAA HRRR storm ingredients and storm reports,
USFS tree canopy and Census housing data. The pipeline runs locally on DuckDB and dbt;
models are compared in a benchmark suite tracked with MLflow; results are served in a
Streamlit dashboard packaged with Docker.

## What it does

1. **Predicts** for every county and every 6-hour block whether ≥ 1%, 5% or 10% of
   customers lose power.
2. **Scores new outages separately** from ongoing ones. Outages persist, so a model can
   look accurate by predicting "still out"; the hard and useful part is the *onset*.
3. **Explains** risk with storm ingredients (wind, gusts, shear, instability, rain, ice)
   *and* place: tree canopy, housing age, density, and each county's outage history.
4. **Scores resilience**: outage hours per customer, events per year, how often a reported
   storm turns into an outage, repeat outages.

## Results

PR-AUC on **new outages** (onset blocks), XGBoost (800 trees, depth 4) trained on
2020–2024, with settings chosen on 2024 and checked over five seeds, tested once on 2025.
For rare events a model with no skill scores the event rate, shown for reference.

| Outage size | New-outage rate | Climatology baseline | Weather only | + place | + recent outages |
|---|---|---|---|---|---|
| **Next year** (train 2020–2024 → test 2025) | | | | | |
| ≥ 1% | 1.97% | 0.032 | 0.116 | 0.145 | **0.153** |
| ≥ 5% | 0.53% | 0.009 | 0.068 | 0.091 | **0.106** |
| ≥ 10% | 0.26% | 0.005 | 0.047 | 0.062 | **0.083** |
| **Unseen counties** (5-fold by county, 2020–2025) | | | | | |
| ≥ 1% | 1.73% | 0.016 | 0.109 | 0.110 | **0.122** |
| ≥ 5% | 0.46% | 0.004 | 0.070 | 0.071 | **0.086** |
| ≥ 10% | 0.22% | 0.002 | 0.054 | 0.054 | **0.068** |

Source: `ml/results/leaderboard_final_2025.md`; settings from `tune.yaml` and
`seeds_tune.yaml`, feature choices from `seeds_ablate.yaml`.

What the numbers say:

- **Weather alone predicts new outages 6–24× better than chance**, more so for bigger outages.
- **More years of storms helped more than any feature**: training on 2020–2024 instead of
  2024 alone lifted every score by 17–28% on the same 2025 test (`years_2020.yaml`,
  `years_2024.yaml`).
- **Place helps for known counties, not new ones**: +25–34% on the next year, about zero
  on unseen counties.
- **Of the 1% of calm county-blocks the model ranks riskiest, about 1 in 7 become a ≥ 5%
  outage** (26× the base rate), catching 26% of all new ≥ 5% outages.
- **On new outages the model is a weather model**: surface wind, minimum temperature,
  county size and wind × rain lead. Scored on all blocks, the previous block's outage is
  seven times any weather or place feature — persistence, not prediction.
- **Tuning barely matters**: the top ten settings on 2024 sit within ±1.2%, about the
  seed-to-seed spread. Up-weighting rare events hurt.
- **Tree canopy: small but real, once tested properly.** With LightGBM on one year it looked
  strong (−12 to −22% without it); with XGBoost it shrank or reversed. Over five seeds and
  five years, removing it lowers the score with every seed in three of four settings
  (−2 to −3%).
- **Left out:** rain in the days before a storm (mixed across seeds) and as-of outage history
  (no gain on the validation year).

### How it compares

PR-AUC on new ≥ 5% outages, next year (`ml/results/leaderboard_official.md`,
`ml/results/leaderboard_weathernext.md`). Official forecasts are taken as they stood when
the block started; the model's HRRR weather covers the block itself.

| Approach | Known | PR-AUC |
|---|---|---|
| NWS warnings in force at block start (event rate per combination) | in advance | 0.024 |
| SPC Day 1 outlook (event rate per risk level) | in advance | 0.033 |
| Warnings + outlook | in advance | 0.044 |
| weathernext-outage-forecasting's setup, reproduced on this data | during the block | 0.053 |
| This model | during the block | 0.106 |
| This model with warnings + outlook as features | during the block | **0.122** |

- **The model scores 2.4× the official forecasts** and gains another 15% (16% on unseen
  counties) when given them as inputs.
- **Warnings are counted only if in force at the block's start.** Counting any warning that
  touched the block nearly doubled their score, because most severe thunderstorm and
  tornado warnings are issued as the storm, and often the outage, arrives.
- **Not a fair race yet**: the model sees the block's weather, the forecasts didn't. Matching
  lead times needs weather forecasts issued before the block (roadmap).
- The weathernext row reproduces that project's method (weather-only features, class-weighted
  boosted tree, 80/20 county-date hash split) with HRRR in place of WeatherNext. On its own
  split it scores 0.059, and its precision at a 0.5 cut-off is 2%.

### What it would be worth

If a utility had staged repair crews wherever each forecast pointed in 2025, how much
would it have saved? `pixi run value` (`ml/value.py`) scores every forecast on the same
new outages, two ways:

- **Relative economic value** (the cost-loss model used to value weather forecasts), which
  needs no dollar figures: the share of a perfect forecast's savings captured. The model
  reaches 0.52; warnings + outlook 0.34, the SPC outlook 0.31, NWS warnings 0.09.
- **Dollars**: customer outage costs from Berkeley Lab's ICE models and a typical customer
  mix, under four scenarios (a staged crew shortens outages by 10% or 25%; staging costs
  $5,000 or $20,000 per county per 6 hours). Every forecast stages by the same rule, using
  2020–2024 data only.

| Net savings in 2025 | Range over the four scenarios |
|---|---|
| Perfect forecast | $11.6M to $99.5M |
| **This model** | **$3.5M to $38.8M** |
| Warnings + outlook | −$14.9M to −$0.6M |
| SPC outlook | −$18.9M to −$1.4M |
| NWS warnings | −$57.7M to $2.0M |

The estimate: **about $4–39 million saved in 2025**, where acting on the official
forecasts would mostly have lost money: they point at far more counties than lose power.
At each forecast's best cutoff in hindsight, the model still saves about 3× as much.
Almost all the avoided cost is businesses' (for households alone, staging never pays), the
figures are customers' losses rather than the utility's, and like every score here they are
a best case because the weather inputs are near-observed. Results:
`ml/results/value_2025.csv`, `ml/results/value_curves_2025.csv`.

### Limitations

- **Weather is short-range, not a 24–48 h forecast.** The HRRR archive stitches the first
  hours of each model run, which is close to observed weather. Scores are an upper bound
  for planning a day ahead.
- **One test year.** Settings were chosen on 2024 and 2025 was scored once, but a single
  test year gives no confidence interval; the seed spread (about ±1%) measures model noise
  only.
- **One weather point per county.** Storm winds are local; a county-wide grid would be better.
- **Canopy is county-wide** and correlated with rurality and the serving utility (its link
  to outages comes almost entirely from Missouri's Ozark counties), so its effect is an association,
  not a cause.
- **EAGLE-I coverage is patchier before 2020**, which limits how far back training can go.
- **St. Louis City and County are one region**: EAGLE-I records the County's outages under
  the City's code from mid-2020 to 2024.

## How it's built

```
ingest/ (Python)          dbt/ (SQL on DuckDB)                    ml/ (Python)                 app/
EAGLE-I, HRRR,     ──►  staging → intermediate → marts   ──►  benchmark suite (MLflow)   ──►  Streamlit
storm reports,          47 tests; 3.5M-row modeling table      YAML configs, 3 splits,        (Docker)
canopy, Census          + resilience scorecard                  onset + all-block metrics
```

| Layer | Tool |
|---|---|
| Environment | [pixi](https://pixi.sh) — one lock file; `default`, `app` and `ci` environments |
| Storage / SQL | [DuckDB](https://duckdb.org) |
| Transformations | dbt Core + dbt-duckdb, dbt_utils tests |
| Geo | geopandas, rasterio |
| ML | XGBoost, LightGBM, scikit-learn, MLflow |
| Dashboard | Streamlit, Plotly |
| Packaging | Docker (linux/amd64), Hugging Face Spaces |
| Quality | pytest, ruff, GitHub Actions |

Design choices worth knowing:

- **Region × 6-hour block** is the unit; the label is the block's peak % of customers out.
- **Missing rows are zeros only when EAGLE-I was running.** A national "heartbeat" (any
  county in the U.S. reporting) separates "no outages" from "no data".
- **Leakage guards:** history features come from 2020–2023 only; recent-outage features
  use previous blocks; storm reports are context, never inputs.
- **Validation:** next year (time) and held-out counties (spatial), always against
  baselines. A random region-day split is in the code to show how it overstates skill.
- **The dashboard reads precomputed Parquet only** — it never runs a model.

The data traps found along the way (a renamed column in 2023, duplicated snapshots in
2025, a raster whose no-data value was a real value, county codes swapped for years, and
more) are in [docs/data-notes.md](docs/data-notes.md).

## Quick start

```bash
pixi install
# EAGLE-I outages: manual download — see data/README.md
pixi run fetch-counties && pixi run fetch-tree-canopy && pixi run fetch-acs && pixi run fetch-storm-events
pixi run fetch-weather 2024 2025      # rate-limited (free tier): ~a day for 216 counties
pixi run build                        # dbt: every model + test
pixi run train                        # quick benchmark → ml/results/
pixi run export-app && pixi run app   # dashboard at http://localhost:8501
```

`docker compose up --build` runs the dashboard in a container.

## Repository layout

| Folder | Contents |
|---|---|
| `ingest/` | download scripts, one per source |
| `dbt/` | SQL models (staging → intermediate → marts), seeds, tests |
| `ml/` | data loading, splits, model registry, metrics, benchmark runner, configs, results |
| `app/` | Streamlit dashboard |
| `notebooks/` | `explore_warehouse` (inspect tables), `benchmark_lab` (try configs interactively) |
| `tests/` | pytest: benchmark machinery and dashboard pages |
| `scripts/` | download queue, Hugging Face publishing |
| `legacy/` | the first St. Louis hourly prototype |
| `docs/` | [data dictionary](docs/data-dictionary.md), [data notes](docs/data-notes.md), [decisions](docs/decisions.md), [development guide](docs/development.md), [roadmap](docs/roadmap.md) |

## Data sources

- **Power outages:** Tansakul, V. et al. (2023). *EAGLE-I Power Outage Data.* Oak Ridge
  National Laboratory. https://doi.org/10.13139/ORNLNCCS/1975202
- **Storm ingredients:** NOAA High-Resolution Rapid Refresh (HRRR), via the
  [Open-Meteo](https://open-meteo.com) Historical Forecast API.
- **Storm reports:** NOAA NCEI Storm Events Database; NWS zone–county correlation file.
- **Official forecasts:** NWS warnings and SPC Day 1 convective outlooks, archived by the
  Iowa Environmental Mesonet.
- **Tree canopy:** USDA Forest Service / NLCD Tree Canopy Cover 2021, via MRLC.
- **Housing and population:** U.S. Census Bureau, ACS 2020–2024 5-year estimates.
- **County boundaries:** U.S. Census Bureau cartographic boundary files (2023).
- **Airport weather (prototype):** NOAA NCEI Global Hourly (ISD), AWS Open Data.

Full source list with URLs: [docs/data-dictionary.md](docs/data-dictionary.md#where-the-data-comes-from).
