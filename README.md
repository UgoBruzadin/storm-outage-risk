# ⚡ Storm Outage Risk — Missouri & Illinois

> Which counties will lose power in the next few hours, early enough to send repair crews?

A county-level power-outage model for the 216 counties of Missouri and Illinois, built on public data: DOE EAGLE-I
outage records, NOAA HRRR weather and the HRRR forecast archive, NWS warnings and SPC outlooks, USFS tree canopy and
Census housing data. The pipeline runs locally on DuckDB and dbt; results are served on a
[story page](https://ugobruzadin.github.io/storm-outage-risk/), a
[write-up](https://ugobruzadin.github.io/storm-outage-risk/writeup/) and a
[Streamlit dashboard](https://storm-outage-risk.streamlit.app).

Iowa, Indiana and Michigan are being added (`dbt/seeds/study_states.csv`; early results in
[E50](docs/experiments.md)). Every number below is still Missouri and Illinois.

## Live forecast (beta)

The story page opens with a live map, updated from [storm-outage-live](https://github.com/UgoBruzadin/storm-outage-live),
which saves each forecast before the weather happens. The live model (frozen at tag `live-v1.1`, trained on 2020–2025) is
the headline recipe without current outage data, which isn't available as it happens: 2.2× (1.8–3.0×) warnings + outlook
on 2025, against 2.4× for the headline model below ([E43](docs/experiments.md)). See [live/README.md](live/README.md). The
forecasts haven't been graded yet: that needs EAGLE-I's release. Experimental: don't use it for safety decisions.

## What it does

1. **Every hour, for every county, predicts a new outage two hours ahead:** the chance that at least 5% of customers
   lose power in the six hours starting two hours later, in a county with no outage in the day before.
2. **Uses only what was known at the time:** the weather so far, the HRRR forecasts issued before the decision,
   warnings and outlooks in force, outages so far in the county and its neighbours, and what the place is like. A
   [pipeline audit](docs/audit.md) checks that no input sees the future.
3. **Gives each prediction a range** from the last five HRRR runs: how much they disagree, not a 95% interval.
4. **Scores resilience:** outage hours per customer, events per year, how often a reported storm turns into an outage.

## Results

Trained on 2020–2024. Base features and settings were chosen on 2024, but the forecast versions were compared on 2025,
so it isn't a pristine test: June–December 2024 gives a second check (2.8×), and the frozen live model is the clean test.
PR-AUC on new ≥ 5% outages, two hours
ahead; 95% ranges from resampling 2025's storm days, ratios paired on the same days
([docs/experiments.md](docs/experiments.md), E19–E26).

| What the model knows | PR-AUC (95% range) | vs. warnings + outlook |
|---|---|---|
| NWS warnings + SPC outlook alone (what utilities have today) | 0.039 (0.020–0.062) | 1× |
| Weather observed so far, warnings, outlook, neighbours, place | 0.064 (0.035–0.096) | 1.6× (1.4–2.2×) |
| + the latest HRRR forecast | 0.088 (0.051–0.134) | 2.2× (1.9–3.0×) |
| **+ the last five HRRR forecasts (headline model)** | **0.094 (0.054–0.143)** | **2.4× (2.0–3.3×)** |
| Ceiling: knowing the window's actual weather | 0.100 (0.058–0.149) | 2.5× (2.1–3.4×) |

- **Every comparison with the official forecasts is significant** (paired storm-day permutation test, p ≤ 0.001).
  The ceiling is not significantly better than the headline model (p = 0.08).
- **Alerting on the riskiest 0.75% of county-hours,** 15% of alerts were followed by a new outage (31× the 0.49% base
  rate) and they caught 30% of 2025's 1,436 new outages in time. The official forecasts, alerting as often, were right
  11% of the time and caught 17%. So about 85% of alerts weren't followed by a new outage and about 70% of outages got
  no alert: it says where to look first, not what will happen.
- **The probabilities are calibrated** up to about 20% (outages followed about as often as predicted); above 20% they
  run a little high. Grouped by prediction, the share of outages that followed falls inside the group's average range
  from the five runs. That's a check on groups, not a validated prediction interval for any one county.
- **The first version scored 0.106 by seeing the storm it predicted:** it summarized the weather *during* the six
  hours it scored. With weather only up to the decision it fell to 0.043; rebuilt hour by hour with forecasts as
  issued, it recovers most of that honestly.
- **Tree canopy is a small, real signal:** removing it costs about 3%, with every seed. By state, it helps the model
  in Illinois (+3.0%) and barely in Missouri (+0.4%), although the county correlation with storm damage is the other
  way round.

### What it would be worth

If a utility had staged repair crews on the model's alerts in 2025, customer outage costs avoided (Berkeley Lab ICE
models, typical customer mix) minus staging costs, under four scenarios (crews shorten outages 10% or 25%; staging
costs $5,000 or $20,000 per county per 6 hours):

| Net savings in 2025, staging 2 hours ahead | Range over the four scenarios |
|---|---|
| Perfect foresight | $18.0M to $113.7M |
| **Model + last five HRRR forecasts** | **$0.7M to $24.4M** |
| Model, weather observed so far | −$2.1M to $28.2M |
| Warnings + outlook | −$19.2M to −$3.2M |

The forecast version uses its probabilities as they are; calibrating them on 2024 forecasts changed the estimate
little. Almost all the avoided cost is businesses'. Code: `ml/value_hourly.py`, `ml/calibrate_forecasts.py`.

### Limitations

- **Few test years for the full recipe.** The model without forecasts beat the official forecasts on each of 2022–2025
  (1.6–2.1×), but the headline recipe has only been tested on June–December 2024 and 2025: the archive doesn't hold enough forecast
  hours before June 2024. The ranges cover which storms hit 2025, not
  how different another year could be.
- **Trained on actual weather.** The headline model learned from what happened and is scored on forecasts, so its highest
  probabilities run a little high. Training on forecasts instead scored lower (2.0× against 2.3× with the newest run on
  2025; [E40](docs/experiments.md)).
- **The live forecast isn't graded yet.** That needs EAGLE-I's 2026 data, which comes out about a year later. Training saw
  warnings' final end times, while the live forecast only knows the end scheduled at that moment, and when the newest
  HRRR run isn't ready a forecast uses four runs instead of five.
- **Archive timestamps.** Each hour's weather and outage counts are used as soon as the hour ends; operationally HRRR
  analyses arrive about an hour late (the forecast runs already allow two hours).
- **One weather point per county**, county-wide canopy, and EAGLE-I coverage that is patchy before 2020.
- **St. Louis City and County are one region**: EAGLE-I records the County's outages under the City's code from mid-2020
  to 2024.

## How it's built

```
ingest/ (Python)          dbt/ (SQL on DuckDB)                    ml/ (Python)                    site/ + app/
EAGLE-I, HRRR and  ──►  staging → intermediate → marts   ──►  moving-window benchmark,     ──►  story page, write-up,
its forecast             61 tests; 15M-row hourly table          forecast test, bootstrap,         Streamlit (Docker)
archive, NWS, SPC,       + resilience scorecard                  significance, audit
canopy, Census
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

- **Region × hour** is the unit: a decision every hour about the six hours starting two hours later. Features look
  only backwards from the decision; the label only forwards.
- **Missing rows are zeros only when EAGLE-I was running.** A national "heartbeat" (any
  county in the U.S. reporting) separates "no outages" from "no data".
- **Leakage guards:** every input is known at the decision, checked by recomputing inputs from the raw tables
  (`ml/audit.py`); forecasts come from runs issued before it; storm reports are context, never inputs.
- **Validation:** a validation year (2024) for the base model's choices, a test year (2025) that the forecast versions were also compared on, storm-day bootstrap
  ranges and paired permutation tests, always against the official forecasts.
- **The dashboard reads precomputed Parquet only** — it never runs a model, and shows 2025, not the live forecast.

The data traps found along the way (a renamed column in 2023, duplicated snapshots in
2025, a raster whose no-data value was a real value, county codes swapped for years, and
more) are in [docs/data-notes.md](docs/data-notes.md).

## Quick start

```bash
pixi install
# EAGLE-I outages: manual download — see data/README.md
pixi run fetch-counties && pixi run fetch-tree-canopy && pixi run fetch-acs && pixi run fetch-storm-events
pixi run fetch-weather 2024 2025      # rate-limited (free tier): ~a day for 216 counties
pixi run fetch-hrrr-forecast 2024-12-31 2025-12-31   # HRRR runs as issued (~1 min per day)
pixi run build                        # dbt: every model + test
pixi run python -m ml.moving_window   # the hourly benchmark → ml/results/
pixi run python -m ml.forecast_test && pixi run python -m ml.forecast_ensemble
pixi run export-app && pixi run python -m ml.export_hourly && pixi run app   # dashboard at http://localhost:8501
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
| `docs/` | [data dictionary](docs/data-dictionary.md), [data notes](docs/data-notes.md), [decisions](docs/decisions.md), [experiments](docs/experiments.md), [audit](docs/audit.md), [development guide](docs/development.md), [roadmap](docs/roadmap.md) |

## Data sources

- **Power outages:** Tansakul, V. et al. (2023). *EAGLE-I Power Outage Data.* Oak Ridge
  National Laboratory. https://doi.org/10.13139/ORNLNCCS/1975202
- **Storm ingredients:** NOAA High-Resolution Rapid Refresh (HRRR), via the
  [Open-Meteo](https://open-meteo.com) Historical Forecast API; HRRR forecasts as issued from the University of Utah's
  hrrrzarr archive on AWS.
- **Storm reports:** NOAA NCEI Storm Events Database; NWS zone–county correlation file.
- **Official forecasts:** NWS warnings and SPC Day 1 convective outlooks, archived by the
  Iowa Environmental Mesonet.
- **Tree canopy:** USDA Forest Service / NLCD Tree Canopy Cover 2021, via MRLC.
- **Housing and population:** U.S. Census Bureau, ACS 2020–2024 5-year estimates.
- **County boundaries:** U.S. Census Bureau cartographic boundary files (2023).
- **Airport weather (prototype):** NOAA NCEI Global Hourly (ISD), AWS Open Data.

Full source list with URLs: [docs/data-dictionary.md](docs/data-dictionary.md#where-the-data-comes-from).
