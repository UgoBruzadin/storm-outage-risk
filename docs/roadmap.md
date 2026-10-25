# Roadmap

Tick boxes as you go — this file is the project's to-do list. Each milestone ends with a commit (or a merged branch) and its check numbers written down.

## ✅ 0 — Repository setup
- [x] Repo layout, pixi environment, `.gitignore` (data and secrets stay out of git)
- [x] Carry over the SQL pipeline, NOAA downloader, model playground
- [x] `pixi run build` rebuilds everything; check numbers match the sandbox
- [x] Push to GitHub (private for now; make public when ready to show)
- [ ] Pick a license (MIT is the usual choice for portfolio code)

## 1 — Move the SQL into dbt
*You learn: dbt models, sources, tests, docs, lineage.*
- [x] Install `dbt-duckdb` (dbt Core 1.12 from PyPI); project skeleton in `dbt/`
- [x] Declare the raw CSVs as **sources**; St. Louis counties as a **seed**
- [x] Worked example: `stg_noaa__kstl_hourly` + tests
- [ ] Split `merge_all.sql` into one model per table: `staging/` (cleaned raw), `intermediate/` (hourly, grid, heartbeat), `marts/` (merged tables)
- [ ] Turn every `-- Check:` comment into a **test**: `unique`, `not_null`, `accepted_values`, row counts
- [ ] `dbt docs generate` — screenshot the lineage graph for the README
- [ ] `pixi run build` now runs `dbt build`; delete `sql/` and `scripts/build_warehouse.py`

## 2 — Expand the data to all of Missouri + Illinois
*You learn: ingestion scripts, APIs, nearest-neighbour joins.*
- [ ] Outages for all 216 regions (started: `sql/build_mo_il.sql`)
- [ ] NOAA Storm Events for MO + IL — defines "a storm hit this county"
- [ ] Hourly weather per county from the nearest NOAA station(s) — 106 active stations in MO + IL
- [ ] **Decide** the forecast source: Open-Meteo historical forecasts vs NOAA GFS/HRRR on AWS vs observed only (see [decisions](decisions.md))

## 3 — County traits (geo features)
*You learn: geopandas, spatial joins, raster zonal statistics.*
- [ ] County shapes (Census TIGER)
- [ ] Tree canopy % per county (USFS/NLCD Tree Canopy Cover)
- [ ] Housing age + density (Census ACS, e.g. table B25035 median year built)
- [ ] Utility per county (HIFLD service territories): investor-owned vs co-op vs municipal

## 4 — Resilience metrics
*You learn: gaps-and-islands, window functions on 15-minute data.*
- [ ] Event detection: group consecutive outage hours into events (exercise: ~32,000 events since 2020)
- [ ] Frequency: events per year, days between events
- [ ] Recovery: time from peak to 90% restored (use 15-minute snapshots, larger events only)
- [ ] Repeat failures: another event within 7 days **with no storm in between**
- [ ] Watch out: a fixed 1% threshold makes small counties look fragile — add a customer floor or size-adjust

## 5 — Model
*You learn: honest validation, calibration, experiment tracking.*
- [ ] One row per county per storm (or per 6-hour block)
- [ ] Baselines first: persistence, climatology
- [ ] LightGBM / HistGradientBoosting; track runs in MLflow
- [ ] Validate on held-out **counties** and later **years**; resilience features computed from training years only
- [ ] Core experiment: does adding tree canopy / housing age beat weather alone on unseen counties?
- [ ] Calibration plot, feature importance, error analysis per county

## 6 — Publish results
- [ ] Hugging Face account + dataset repo; token in `.env` only
- [ ] `pixi run publish`: export app tables to Parquet (< ~200 MB total) and upload

## 7 — Streamlit app
- [ ] Map: county risk (Plotly or pydeck)
- [ ] Storm replay: predicted vs actual through a storm
- [ ] Resilience scorecard
- [ ] Model page: metrics, calibration, what drives risk
- [ ] Develop against local Parquet; switch to `hf://` paths for deployment

## 8 — Docker, deploy, CI
- [ ] Dockerfile (pixi base image) + `compose.yaml`
- [ ] Deploy to a Hugging Face Space
- [ ] GitHub Actions: ruff + pytest + dbt tests on a small sample

## 9 — Write-up
- [ ] README: screenshots, live link, key findings, limitations
- [ ] A short "what I learned / data traps" section (from [data notes](data-notes.md))
