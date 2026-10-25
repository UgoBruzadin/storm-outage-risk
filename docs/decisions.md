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
| open | **Forecast weather source** | Options: Open-Meteo historical forecast API (easy, check archive depth), NOAA GFS/HRRR on AWS (authentic, harder), observed-only (simplest, reframes as "how weather becomes outages") |
| open | **License** | MIT is typical for portfolio code; data keeps its own terms |
