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

PR-AUC on **new outages** (onset blocks), XGBoost with storm, place, history and
recent-outage features. For rare events a model with no skill scores the event rate, shown
for reference.

| Outage size | New-outage rate | Climatology baseline | Weather only | + place + history | + recent outages |
|---|---|---|---|---|---|
| **Next year** (train 2024 → test 2025) | | | | | |
| ≥ 1% | 1.97% | 0.028 | 0.094 | 0.118 | **0.134** |
| ≥ 5% | 0.53% | 0.008 | 0.051 | 0.061 | **0.087** |
| ≥ 10% | 0.26% | 0.004 | 0.030 | 0.041 | **0.062** |
| **Unseen counties** (5-fold by county) | | | | | |
| ≥ 1% | 1.86% | 0.018 | 0.125 | 0.148 | **0.156** |
| ≥ 5% | 0.50% | 0.005 | 0.086 | 0.101 | **0.111** |
| ≥ 10% | 0.25% | 0.002 | 0.064 | 0.077 | **0.091** |

Source: `ml/results/leaderboard_quick.md` (fixed hyperparameters). A 264-run grid search
(`ml/results/leaderboard_full.md`) adds up to +0.01.

What the numbers say:

- **Weather alone predicts new outages 10–30× better than chance**, and every added
  feature group helps on both splits.
- **Bigger outages are more predictable relative to their base rate.** Of the 1% of calm
  county-blocks the model ranks riskiest, about 1 in 8 become a ≥ 5% outage (24× the base
  rate), and together they catch about a quarter of all new ≥ 5% outages.
- **On new outages the model is a weather model**: its top features are surface wind,
  shear × instability and wind × rain. Scored on all blocks, the previous block's outage
  outweighs everything else fifteenfold — persistence, not prediction.
- **Model family barely matters.** Tuned XGBoost and LightGBM tie; XGBoost trains ~1.6× faster.
- **Up-weighting rare events hurt** (`scale_pos_weight`), and shallow trees generalized
  better to the next year.
- **Tree canopy shows why the comparison spans several models.** With LightGBM alone,
  removing canopy cost 12% (≥ 5%) and 22% (≥ 10%) of next-year PR-AUC — it looked like a
  strong feature. The same ablation with XGBoost, and with models trained only on new
  outages (`ml/results/leaderboard_onsets.md`), shrank the effect to a few percent and
  sometimes reversed it. Across models, canopy's effect is weak and inconsistent.

### How it compares

PR-AUC on new ≥ 5% outages, next year (`ml/results/leaderboard_official.md`,
`ml/results/leaderboard_weathernext.md`):

| Approach | PR-AUC |
|---|---|
| SPC Day 1 outlook (event rate per risk level) | 0.032 |
| NWS warnings in force (event rate per warning combination) | 0.044 |
| Warnings + outlook | 0.051 |
| weathernext-outage-forecasting's setup, reproduced on this data | 0.032 |
| This model | 0.091 |
| This model with warnings + outlook as features | **0.132** |

- **The model beats the official forecasts** (1.8× warnings + outlook), at every outage
  size and on both splits, and gains another 45% when given them as inputs.
- The outlook is always issued before the block; warnings are often issued during it, the
  same timing as the HRRR inputs.
- The weathernext row reproduces that project's method (weather-only features, class-weighted
  boosted tree, 80/20 county-date hash split) with HRRR in place of WeatherNext. On its own
  split it scores 0.072, and its precision at a 0.5 cut-off is 3%.

### Limitations

- **Weather is short-range, not a 24–48 h forecast.** The HRRR archive stitches the first
  hours of each model run, which is close to observed weather. Scores are an upper bound
  for planning a day ahead.
- **One test year.** The next-year split trains on 2024 and tests on 2025; weather for
  2018–2023 extends this. No confidence intervals yet, so small differences (< 0.005)
  may be noise, and the grid-search maxima were selected on the test year.
- **One weather point per county.** Storm winds are local; a county-wide grid would be better.
- **Canopy is county-wide** and correlated with rurality and the serving utility, so its
  effect is an association, not a cause.
- **St. Louis City and County are one region**: EAGLE-I records the County's outages under
  the City's code from mid-2020 to 2024.

## How it's built

```
ingest/ (Python)          dbt/ (SQL on DuckDB)                    ml/ (Python)                 app/
EAGLE-I, HRRR,     ──►  staging → intermediate → marts   ──►  benchmark suite (MLflow)   ──►  Streamlit
storm reports,          57 tests; 3.5M-row modeling table      YAML configs, 3 splits,        (Docker)
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
