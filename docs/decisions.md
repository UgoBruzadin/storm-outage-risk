# Decisions

A log of design choices and the reasons for them. A changed decision gets a new entry; earlier entries stay as history.

| Date | Decision | Why |
|---|---|---|
| 2026-10 | **DuckDB, local** for all heavy processing | 11 GB of CSVs process in seconds on a laptop; free; same SQL everywhere |
| 2026-10 | **Hourly grain** (start of hour *t*); features use only information available at *t* | Avoids leakage; outages known up to *t − 1*, weather from the :51 report before *t* |
| 2026-10 | **Merge St. Louis City + County** into one region | EAGLE-I mislabels County outages as City for 2020–2024; can't be split reliably |
| 2026-10 | **Train on 2020+** by default | EAGLE-I coverage gaps before 2020 make quiet years look spuriously calm |
| 2026-10 | **Never split randomly**; split by time, later also by held-out counties | Neighbouring hours/counties share storms; random splits leak and inflate scores |
| 2026-10 | **Always report a baseline** (persistence, climatology) | A score means nothing without "compared to what?"; persistence is hard to beat short-term |
| 2026-10 | **Train and evaluate locally; publish only small outputs** to Hugging Face | Free, public, DuckDB reads `hf://` directly; raw data never leaves the laptop |
| 2026-10 | **The app reads precomputed results only** | Fast, small image, free hosting, and the app can't break when model code changes |
| 2026-10 | **dbt** for transformations (planned, milestone 1) | Turns hand-checked row counts into automatic tests; lineage docs |
| 2026-10 | **dbt Core v1 (1.12) + dbt-duckdb from PyPI**, not dbt v2 | Works today with the DuckDB 2.0 warehouse (v2 bundles its own DuckDB, which may not open 2.0 files); Apache-licensed (v2's free build is under a license agreement); nearly all tutorials are v1. Projects mostly carry over — revisit later |
| 2026-10 | Pin `python-dateutil < 3` | pandas pulled 3.0, but dbt-common requires < 3; pandas works with 2.9 |
| 2026-10 | **Weather: HRRR via Open-Meteo's Historical Forecast API**, one point per region, 2024–2025 first | Free; covers the storm ingredients that drive outages (gusts, winds aloft → shear, CAPE, precip, temperature, freezing level); HRRR archive back to 2018. It stitches each run's first hours, so it's *short-range* weather (≈ a perfect 0–6 h forecast), not 24–48 h ahead — true lead-time forecasts are only archived from 2024 (Previous Runs / Single Runs APIs): a next step |
| 2026-10 | **Unit = region x 6-hour block (00/06/12/18 UTC)**, label = peak % out ≥ 5% | 6 h smooths 15-min noise and matches crew planning |
| 2026-10 | **Analysis area = all 216 MO + IL regions** (St. Louis City + County merged) | Place features need many places: with 7 regions, canopy is just a region ID |
| 2026-10 | **Coverage QC from the national heartbeat** (≥ 12 of 24 snapshots in a block), not per-county row counts | A county's own row count can't tell "no outages" from "no data" |
| 2026-10 | **Resilience metrics from 2020–2023 only**, used as features for 2024–2025 models (superseded below by as-of history) | Known before the train/test years → no leakage; dbt var to change the window |
| 2026-10 | **Storm Events are context, never model inputs** | Reports are written after the fact; using them would leak the answer |
| 2026-10 | **Three splits reported**: time (2024 → 2025), held-out counties (5-fold by region), random region-days | Time = next year; county = new places (the honest test for place features); random = the common random-day evaluation, kept to show its optimism |
| 2026-10 | **MLflow** with a local SQLite store (`data/mlflow.db`) | Current tracking tool, nothing to host; the summary CSV in `ml/results/` is the git-tracked record |
| 2026-10 | **Separate pixi environments**: default (everything), `app` (Docker), `ci` (tests + dbt parse) | Small image (561 MB), fast CI, one lock file |
| 2026-10 | **Hugging Face, private by default** (`--public` to open up) | Publishing is opt-in; a private dataset works too (the app reads it with a DuckDB secret) |
| 2026-10 | **Tried 8 states** (MO, IL + AR, IA, IN, KS, KY, TN), then **paused: back to MO + IL**, more years first. Not the whole country | More places and storms for the same storm climate. National was ruled out by the weather quota (~160k Open-Meteo calls for 2 years) and by regime mixing (hurricanes, wildfire shutoffs). None of the added states has independent cities, so St. Louis stays the only merged region |
| 2026-10 | **The study area lives in one seed**, `dbt/seeds/study_states.csv`, read by dbt and the ingest scripts; models renamed `mo_il` → `study` | Adding a state is one CSV line + re-running fetch/build; no hard-coded state lists |
| 2026-10 | **Train on 2020–2024, choose settings on 2024, test once on 2025** | Four more years of storms lifted onset PR-AUC 13–30%; a validation year removes the "tuned on the test year" weakness |
| 2026-10 | **History features "as of" each year** (3 years before Jan 1 of the row's year), replacing the fixed 2020–2023 window for the model | A fixed window overlaps the new training years. The scorecard keeps 2020–2023 for display |
| 2026-10 | **Final model without history features** | No gain on the 2024 validation year (0.080 vs 0.081 onset PR-AUC) |
| 2026-10 | **Fixed row order in `ml/data.load`** | DuckDB returned rows in varying order and row subsampling depends on it: identical runs differed by ~1%, as much as the effects being judged. All reported configs were rerun |
| 2026-10 | **Feature and setting decisions averaged over 5 seeds** (`seeds_tune.yaml`, `seeds_ablate.yaml`) | Single runs can't separate effects of ~1–2% from seed noise (±0.0007 onset PR-AUC) |
| 2026-10 | **Final model keeps canopy, leaves out antecedent rain** (`wet_soil`) | Over 5 seeds on the 2024 validation year, removing canopy lowered onset PR-AUC with every seed in 3 of 4 settings (−2.3 to −2.8%). Rain helped on unseen counties at ≥ 5% (5 of 5 seeds) but hurt next year at ≥ 10% (1 of 5): mixed, not adopted |
| 2026-10 | **Final XGBoost: 800 trees, learning rate 0.03, depth 4, min child weight 20** | Best on the 2024 validation year (`tune.yaml`); larger leaves helped across the grid |
| 2026-10 | **Value forecasts by the cost-loss model, dollars as scenarios** (`ml/value.py`) | Relative economic value compares forecasts without dollar assumptions. Dollars use Berkeley Lab's ICE outage-cost models; crew effect (10%/25%) and staging cost ($5k/$20k) have no published source, so they are scenarios. Every forecast stages by the same no-peeking rule; official baselines are fitted on onset periods so their probabilities answer the same question |
| 2026-10 | **Lead-time test on 6-hour blocks** (`ml/lead_time.py`): weather from before the block only | With weather up to the block's start, onset PR-AUC falls from 0.106 to 0.043, about the official forecasts (0.044); with warnings + outlook added, 0.084. Most of the reported skill comes from knowing the block's own weather, so it is reported as the best case |
| 2026-10 | **Moving-window table** (`mart_study__region_1h`, `ml/moving_window.py`): a decision every hour about the 6 hours starting 0–6 h later, every input known at the decision | Matches how crews are called out (any hour, not 00/06/12/18 UTC); lead time is one table; outages "now" come from the 15-min snapshots, not the last full block. Scored by new outages caught in time and alert episodes, since overlapping windows make row counts misleading. Becomes the main benchmark |
| open | **Per-region coverage gaps** (a utility drops out of / joins EAGLE-I for whole years) | Proposed: mark a region-year untracked when < 2% of its blocks have outages but a typical year has > 15% → label unknown. Thresholds to decide |
| open | **License** | MIT is typical for portfolio code; data keeps its own terms |
