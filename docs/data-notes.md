# Data notes

Everything surprising found in the raw data, and what the pipeline does about it. Add to this file whenever a number looks wrong — it's also great README material.

## EAGLE-I outages (DOE / ORNL)

| Quirk | Effect if ignored | Fix |
|---|---|---|
| Only counties with ≥ 1 customer out get a row; **no row = 0** | Averages too high; a model never sees quiet hours | Build a full county × hour grid, LEFT JOIN, fill 0 |
| Snapshots every 15 minutes, **UTC** | Off by 5–6 h vs local time | Keep everything in UTC |
| **2023 file names the count column `sum`**, not `customers_out` | 2023 looks like a year with no outages | `union_by_name = true` + `coalesce(customers_out, "sum")` |
| 2024 file has an extra `total_customers` column | Glob read fails ("schema mismatch") | `union_by_name = true`, then `EXCLUDE` it |
| Some snapshots have a **blank** `customers_out` (16,837 in the St. Louis counties) | Blank hours become fake zeros | In the grid, only "no row" becomes 0; a row with a blank value stays NULL |
| **EAGLE-I itself was down** for 356 hours (no snapshot anywhere in the US) | Down hours look like perfect-power hours | "Heartbeat" table of hours with any national snapshot; no heartbeat → NULL |
| **St. Louis County's outages filed under St. Louis City's FIPS (29510)**, mid-2020 → 2024; County shows 0 for 2022–2024; back in 2025 | Wrong per-county numbers; a fake "78% of the City out" in July 2023 | Merge City + County into one region `29189+29510`; sum per snapshot, then max per hour |
| **Coverage grew over time** (Missouri ≈ 79% of customers tracked in 2018 → ≈ 95% from 2019; Jefferson Co. shows ~0% outage-hours in 2018) | Fake upward trend; untracked years look calm | Train on 2020+ by default |
| `MCC.csv` (customers per county): FIPS stored as text **without leading zeros**; last row is `Grand Total` | Join misses some states; a fake "county" | `lpad(County_FIPS, 5, '0')`; exclude `Grand Total` |
| Coverage varies by year at the snapshot level too (2017 low everywhere) | — | See `coverage_history.csv` (state-level) |

## NOAA Global Hourly (ISD)

| Quirk | Fix |
|---|---|
| Files moved from ncei.noaa.gov to the AWS bucket `noaa-global-hourly-pds` | `ingest/fetch_noaa.py` uses the bucket |
| Several values packed in one text field, ×10, with `9999`-style missing codes (`TMP = '+0039,1'` = 3.9 °C) | `split_part` → `nullif(…, '+9999')` → `::INT / 10.0` |
| Optional columns (`GA4`, `AX4`, …) differ between years | `union_by_name = true` |
| Report types mixed: `FM-15` hourly, `FM-16` specials, `SOD/SOM` daily/monthly summaries | Keep `FM-15` |
| Hourly report at **:51** | +9 minutes so it labels the *next* hour → weather is always from before the outage (no leakage) |
| Some hours have two `FM-15` reports (e.g. 08:50 and 08:51) | `QUALIFY row_number() … = 1` keeps the earliest |
| Gust (`OC1`) only reported when gusty — NULL in ~86% of hours | NULL here means "no gust": fall back to wind speed |
| Thunder almost never in coded `MW1`, but present in the METAR text (`REM`: `TS`, `-TSRA`, `VCTS`, `TSB28E51`) | Regex on `REM` |
| 2025 file ends **2025-08-27** | Grid ends where the shorter dataset ends (`least(...)`) |

## Tooling traps

- conda-forge and Homebrew builds of the DuckDB CLI **can't load official extensions** (e.g. the UI) — use the official build (`curl https://install.duckdb.org | sh`).
- conda-forge's Python DuckDB is 1.5.6, which **can't open files written by DuckDB 2.x** — this repo installs `duckdb==2.0.0` from PyPI.
- Only **one writer** can open a DuckDB file at a time; read-only connections also block writers. Close the UI / restart notebook kernels before `pixi run build`.
- `WHERE` runs **before** window functions — filter years *after* computing lags, or the first lags come out empty.
- DuckDB 2.x: the lambda arrow `x -> …` is deprecated (use `lambda x: …`); in Python, read each `execute()` result before running more SQL on the same connection.
