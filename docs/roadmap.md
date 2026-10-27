# Roadmap

Status of the project, by milestone. Unchecked items are planned next steps.

## ✅ 0 — Repository setup
- [x] Repo layout, pixi environment, `.gitignore` (data and secrets stay out of git)
- [x] Carry over the SQL pipeline, NOAA downloader, model playground
- [x] GitHub repository
- [x] License: MIT

## ✅ 1 — dbt
- [x] dbt Core 1.12 + dbt-duckdb; sources, seed, macros, staging/intermediate/marts
- [x] Tests on every model (unique keys, ranges, regression tests for real bugs)
- [x] `pixi run build` = `dbt build`; old SQL moved to `legacy/`
- [ ] `dbt docs generate` — screenshot the lineage graph for the README

## ✅ 2 — Data for all of Missouri + Illinois
- [x] Outages for 216 regions, 6-hour blocks, national heartbeat QC
- [x] NOAA Storm Events (county + zone events) per block
- [x] HRRR storm ingredients per region via Open-Meteo — 2024–2025
- [x] Backfill HRRR 2020–2023 → train on 2020–2024, validate on 2024, test on 2025
- [ ] Finish HRRR 2018–2019 (downloading)
- [ ] True 24–48 h lead-time forecasts (Open-Meteo Previous Runs / Single Runs APIs, 2024+) for a lead-time evaluation

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
- [x] 6-hour storm-outage classifier, feature-set ablation, time / county / random splits, MLflow
- [x] Benchmark suite: YAML configs, model registry (baselines, logistic, HGB, random forest, LightGBM,
      XGBoost), feature groups, leaderboards in `ml/results/`
- [x] "recent" features: outages in the previous block / 24 h (known at the block's start)
- [x] Run `full.yaml` (grid + canopy ablation, 264 runs) — `ml/results/leaderboard_full.md`
- [x] Results in README
- [ ] Calibration plot; error analysis per county; threshold 1% vs 5%
- [ ] Optuna search instead of grids, once the grid shows which parameters matter

## ✅ 6–8 — App, Docker, CI (first version)
- [x] Streamlit app: overview map, storm replay, scorecard, model page
- [x] Dockerfile (pixi, 561 MB), compose, GitHub Actions (lint, tests, dbt parse, Docker build)
- [x] Hugging Face publishing scripts (private by default)
- [ ] Hugging Face account + token in `.env` → `pixi run publish-data` and `pixi run deploy-space`
- [ ] Make the repo and Space public when ready to show

## 9 — Write-up
- [ ] README: screenshots, live link, key findings, limitations
- [ ] Short "data traps" section from [data notes](data-notes.md)
