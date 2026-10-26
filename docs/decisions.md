# Decisions

A short log of choices and why. When you change your mind, add a new entry instead of editing the old one — the history is the point.

| Date | Decision | Why |
|---|---|---|
| 2026-10 | **DuckDB, local** for all heavy processing | 11 GB of CSVs process in seconds on a laptop; free; same SQL everywhere |
| 2026-10 | **Hourly grain** (start of hour *t*); features use only information available at *t* | Avoids leakage; outages known up to *t − 1*, weather from the :51 report before *t* |
| 2026-10 | **Merge St. Louis City + County** into one region | EAGLE-I mislabels County outages as City for 2020–2024; can't be split reliably |
| 2026-10 | **Train on 2020+** by default | EAGLE-I coverage gaps before 2020 make quiet years look fake-calm |
| 2026-10 | **Never split randomly**; split by time, later also by held-out counties | Neighbouring hours/counties share storms; random splits leak and inflate scores |
| 2026-10 | **Always report a baseline** (persistence, climatology) | A score means nothing without "compared to what?"; persistence is hard to beat short-term |
| 2026-10 | **Train and evaluate locally; publish only small outputs** to Hugging Face | Free, public, DuckDB reads `hf://` directly; raw data never leaves the laptop |
| 2026-10 | **The app reads precomputed results only** | Fast, small image, free hosting, and the app can't break when model code changes |
| 2026-10 | **dbt** for transformations (planned, milestone 1) | Turns hand-checked row counts into automatic tests; lineage docs |
| 2026-10 | **dbt Core v1 (1.12) + dbt-duckdb from PyPI**, not dbt v2 | Works today with the DuckDB 2.0 warehouse (v2 bundles its own DuckDB, which may not open 2.0 files); Apache-licensed (v2's free build is under a license agreement); nearly all tutorials are v1. Projects mostly carry over — revisit later |
| 2026-10 | Pin `python-dateutil < 3` | pandas pulled 3.0, but dbt-common requires < 3; pandas works with 2.9 |
| 2026-10 | **Weather: HRRR via Open-Meteo's Historical Forecast API**, one point per region, 2024–2025 first | Free; same ingredients as WeatherNext (gusts, winds aloft → shear, CAPE, precip, temperature, freezing level); HRRR archive back to 2018. It stitches each run's first hours, so it's *short-range* weather (≈ a perfect 0–6 h forecast), not 24–48 h ahead — true lead-time forecasts are only archived from 2024 (Previous Runs / Single Runs APIs): a next step |
| 2026-10 | **Unit = region x 6-hour block (00/06/12/18 UTC)**, label = peak % out ≥ 5% | Mirrors weathernext-outage-forecasting; 6 h smooths 15-min noise and matches crew planning |
| 2026-10 | **Analysis area = all 216 MO + IL regions** (St. Louis City + County merged) | Place features need many places: with 7 regions, canopy is just a region ID |
| 2026-10 | **Coverage QC from the national heartbeat** (≥ 12 of 24 snapshots in a block), not per-county row counts | weathernext counts a county's own rows, which can't tell "no outages" from "no data" |
| 2026-10 | **Resilience metrics from 2020–2023 only**, used as features for 2024–2025 models | Known before the train/test years → no leakage; dbt var to change the window |
| 2026-10 | **Storm Events are context, never model inputs** | Reports are written after the fact; using them would leak the answer |
| 2026-10 | **Three splits reported**: time (2024 → 2025), held-out counties (5-fold by region), random region-days | Time = next year; county = new places (the honest test for place features); random = weathernext's approach, kept to show its optimism |
| 2026-10 | **MLflow** with a local SQLite store (`data/mlflow.db`) | Current tracking tool, nothing to host; the summary CSV in `ml/results/` is the git-tracked record |
| 2026-10 | **Separate pixi environments**: default (everything), `app` (Docker), `ci` (tests + dbt parse) | Small image (561 MB), fast CI, one lock file |
| 2026-10 | **Hugging Face, private by default** (`--public` to open up) | User wants everything private for now; the app reads a private dataset with a DuckDB secret |
| 2026-10 | **Tried 8 states** (MO, IL + AR, IA, IN, KS, KY, TN), then **paused: back to MO + IL**, more years first. Not the whole country | More places and storms for the same storm climate. National was ruled out by the weather quota (~160k Open-Meteo calls for 2 years) and by regime mixing (hurricanes, wildfire shutoffs). None of the added states has independent cities, so St. Louis stays the only merged region |
| 2026-10 | **The study area lives in one seed**, `dbt/seeds/study_states.csv`, read by dbt and the ingest scripts; models renamed `mo_il` → `study` | Adding a state is one CSV line + re-running fetch/build; no hard-coded state lists |
| open | **Per-region coverage gaps** (a utility drops out of / joins EAGLE-I for whole years) | Proposed: mark a region-year untracked when < 2% of its blocks have outages but a typical year has > 15% → label unknown. Thresholds to decide |
| open | **License** | MIT is typical for portfolio code; data keeps its own terms |
