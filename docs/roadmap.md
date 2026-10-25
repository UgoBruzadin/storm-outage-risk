# Roadmap

Tick boxes as you go — this file is the project's to-do list.

## ✅ 0 — Repository setup
- [x] Repo layout, pixi environment, `.gitignore` (data and secrets stay out of git)
- [x] Carry over the SQL pipeline, NOAA downloader, model playground
- [x] Push to GitHub (private for now; make public when ready to show)
- [ ] Pick a license (MIT is the usual choice for portfolio code)

## ✅ 1 — dbt
- [x] dbt Core 1.12 + dbt-duckdb; sources, seed, macros, staging/intermediate/marts
- [x] Tests on every model (unique keys, ranges, regression tests for real bugs)
- [x] `pixi run build` = `dbt build`; old SQL moved to `legacy/`
- [ ] `dbt docs generate` — screenshot the lineage graph for the README

## ✅ 2 — Data for all of Missouri + Illinois
- [x] Outages for 216 regions, 6-hour blocks, national heartbeat QC
- [x] NOAA Storm Events (county + zone events) per block
- [x] HRRR storm ingredients per region via Open-Meteo — 2024–2025
- [ ] Backfill HRRR 2020–2023 (`pixi run fetch-weather 2020 2021 2022 2023`, ~3–4 days of the free quota) → train on more years
- [ ] True 24–48 h lead-time forecasts (Open-Meteo Previous Runs / Single Runs APIs, 2024+) to replicate weathernext's lead-time evaluation

## ✅ 3 — County traits (geo features)
- [x] County shapes (Census), tree canopy % (USFS/NLCD 2021), housing age + density (ACS 2024)
- [ ] Utility per county (HIFLD service territories): investor-owned vs co-op vs municipal — likely a strong confounder for canopy
- [ ] Canopy near people/lines instead of county-wide (e.g. canopy within developed land or along roads)

## ✅ 4 — Resilience metrics (first version)
- [x] Events (gaps-and-islands on 6-hour blocks), events/yr, outage hours per customer, storm hit rate, 7-day repeats
- [ ] Recovery time from 15-minute snapshots (peak → 90% restored), larger events only
- [ ] Repeats "with no storm in between" (needs Storm Events between the two events)
- [ ] Size-adjusted events (a fixed 1% threshold makes small counties look fragile)

## 5 — Model
- [x] WeatherNext-style 6-hour classifier, feature-set ablation, time / county / random splits, MLflow
- [ ] Full results with all 216 regions → README
- [ ] Calibration plot; error analysis per county; threshold 1% vs 5%
- [ ] LightGBM + a small hyperparameter search (tracked in MLflow)

## ✅ 6–8 — App, Docker, CI (first version)
- [x] Streamlit app: overview map, storm replay, scorecard, model page
- [x] Dockerfile (pixi, 561 MB), compose, GitHub Actions (lint, tests, dbt parse, Docker build)
- [x] Hugging Face publishing scripts (private by default)
- [ ] Hugging Face account + token in `.env` → `pixi run publish-data` and `pixi run deploy-space`
- [ ] Make the repo and Space public when ready to show

## 9 — Write-up
- [ ] README: screenshots, live link, key findings, limitations
- [ ] Short "data traps" section from [data notes](data-notes.md)
