# ⚡ Storm Outage Risk — Missouri & Illinois

> Forecast which counties will lose power in the next 24–48 hours — and explain **why** the same storm hits some places much harder than others.

**Status: work in progress.** Milestone 0 (repo setup) is done; see the [roadmap](docs/roadmap.md).

## What it will do

1. **Forecast** — for every county, the probability that more than X% of customers lose power in the next 24–48 hours.
2. **Explain** — storm strength *and* place: tree canopy, age of the built environment, the utility, past resilience.
3. **Resilience scorecard** — how often each county loses power, how fast it recovers, how often it fails again soon after.
4. **Storm replay** — pick a past storm, watch predicted vs actual outages on the map.

All from open data, in an interactive Streamlit dashboard.

## Why this project

Inspired by [weathernext-outage-forecasting](https://github.com/biplovbhandari/weathernext-outage-forecasting), which joins Google's WeatherNext forecasts with outage data on BigQuery. This project takes the same core idea and changes the parts that matter:

- **Free and local** — DuckDB on a laptop instead of a paid cloud warehouse and forecast subscription.
- **Place matters** — adds county traits (vegetation, housing age, utility, resilience history), which the weather-only approach leaves out.
- **Honest validation** — split by time *and* by held-out counties, always compared against a simple baseline. A random split by county-day lets one storm leak into both train and test.
- **Documented data quality** — the raw data has real traps (see [data notes](docs/data-notes.md)), and each fix is explained and tested.

## Architecture

```
LOCAL (heavy lifting)                                    CLOUD (free, public)
raw CSVs ─► SQL / dbt on DuckDB ─► features ─► model      Hugging Face dataset: small Parquet outputs
 (EAGLE-I,   (tested transforms)    (SQL window  (scikit-       ▲
  NOAA,                              functions)   learn,       │ pixi run publish
  Census…)                                        MLflow) ─────┘
                                                               │ hf://…
                                                  Streamlit app (Docker) on Hugging Face Spaces
```

The app only reads precomputed results — it never runs the model — so it stays fast, small, and free to host.

## Tech stack

| Layer | Tool |
|---|---|
| Environment | [pixi](https://pixi.sh) |
| Storage / SQL | [DuckDB](https://duckdb.org) |
| Transformations | dbt (`dbt-duckdb`) — *milestone 1* |
| Geo | geopandas |
| ML | scikit-learn / LightGBM, MLflow |
| Dashboard | Streamlit |
| Packaging / hosting | Docker, Hugging Face Spaces |
| Quality | pytest, ruff, GitHub Actions |

## Quick start

```bash
pixi install              # create the environment
pixi run fetch-noaa       # download NOAA hourly weather (~90 MB)
# EAGLE-I outages: manual download — see data/README.md
pixi run build            # build data/warehouse.duckdb (~30 s), prints check numbers
```

Then open `notebooks/model_playground.ipynb` with the pixi kernel.

## Repository layout

| Folder | What lives there |
|---|---|
| `ingest/` | scripts that download raw data |
| `sql/` | the current SQL pipeline (moves into `dbt/` in milestone 1) |
| `scripts/` | small runners (`build_warehouse.py`) |
| `notebooks/` | exploration and model experiments |
| `dbt/` | *milestone 1:* SQL models + tests |
| `ml/` | *milestone 5:* feature building, training, evaluation |
| `app/` | *milestone 7:* Streamlit dashboard |
| `tests/` | pytest |
| `data/` | local data, not in git — see `data/README.md` |
| `docs/` | [roadmap](docs/roadmap.md), [data dictionary](docs/data-dictionary.md), [data notes](docs/data-notes.md), [decisions](docs/decisions.md), [walkthrough](docs/walkthrough.md), [working on this project](docs/working-on-this.md) |

## Data sources & credits

- **Power outages:** U.S. DOE / Oak Ridge National Laboratory, EAGLE-I recorded electricity outages — cite using the files shipped with the download (`citation_*.txt`).
- **Weather:** NOAA NCEI Global Hourly (Integrated Surface Database), via the AWS Open Data mirror.
- *Planned:* NOAA Storm Events, USFS/NLCD Tree Canopy Cover, U.S. Census ACS, HIFLD utility service territories.
