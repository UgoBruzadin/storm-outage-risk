# Data notes

Everything surprising found in the raw data, and what the pipeline does about it. Add to this file whenever a number looks wrong — it's also great README material.

## EAGLE-I outages (DOE / ORNL)

| Quirk | Effect if ignored | Fix |
|---|---|---|
| Only counties with ≥ 1 customer out get a row; **no row = 0** | Averages too high; a model never sees quiet hours | Build a full county × hour grid, LEFT JOIN, fill 0 |
| Snapshots every 15 minutes, **UTC** | Off by 5–6 h vs local time | Keep everything in UTC |
| **2023 file names the count column `sum`**, not `customers_out` | 2023 looks like a year with no outages | `union_by_name = true` + `coalesce(customers_out, "sum")` |
| 2024 file has an extra `total_customers` column | Glob read fails ("schema mismatch") | `union_by_name = true`, then `EXCLUDE` it |
| Some snapshots have a **blank** `customers_out` (16,837 in the St. Louis counties) | Blank hours become spurious zeros | In the grid, only "no row" becomes 0; a row with a blank value stays NULL |
| **EAGLE-I itself was down** for 356 hours (no snapshot anywhere in the US) | Down hours look like perfect-power hours | "Heartbeat" table of hours with any national snapshot; no heartbeat → NULL |
| **St. Louis County's outages filed under St. Louis City's FIPS (29510)**, mid-2020 → 2024; County shows 0 for 2022–2024; back in 2025 | Wrong per-county numbers; a spurious "78% of the City out" in July 2023 | Merge City + County into one region `29189+29510`; sum per snapshot, then max per hour |
| **Coverage grew over time** (Missouri ≈ 79% of customers tracked in 2018 → ≈ 95% from 2019; Jefferson Co. shows ~0% outage-hours in 2018) | Fake upward trend; untracked years look calm | Train on 2020+ by default |
| `MCC.csv` (customers per county): FIPS stored as text **without leading zeros**; last row is `Grand Total` | Join misses some states; a "county" that isn't one | `lpad(County_FIPS, 5, '0')`; exclude `Grand Total` |
| Coverage varies by year at the snapshot level too (2017 low everywhere) | — | See `coverage_history.csv` (state-level) |
| **Duplicate snapshots**, early Sept 2025: every snapshot recorded twice (`00:00:00` and `00:00:52`); a few others off the 15-min grid (`:01`, `:16`, `:31`, `:35`) | Blocks with up to 48 "snapshots"; summed regions double-count | `snapshot_time` = rounded to 15 min; one value (max) per county per slot before adding counties |
| **Customer counts too low** for some counties (Worth Co., MO: 418 in MCC for ~2,000 residents) and **one-off spikes** (Boone Co., MO: 311,925 out of ~122k customers on 2019-12-13) | "300% of customers out" | `peak_suspect` when peak > 1.5x customers → percentage NULL; otherwise capped at 100% |
| Utility coverage also varies **within** a state (Jefferson Co., MO ~0% outage-hours in 2018, 7% in 2019, 54% from 2020) | Untracked years look calm | History/resilience window and training start in 2020 |
| **Regions go dark for whole years after 2020** too: Crockett & Obion, TN show outages in ~20–30% of blocks every year, then **0% in 2025**; Wolfe, KY shows 0% in 2020–2021, then ~30–40% | Spurious zeros — for Crockett/Obion in the **test year** | Open: per-region coverage flag (see decisions.md) |

## NOAA Global Hourly (ISD): St. Louis airport station, legacy prototype only

The first prototype (`legacy/`) used one airport station's hourly reports. The county
model uses HRRR via Open-Meteo instead, so nothing in this section limits it.

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
| The station's 2025 file ends **2025-08-27** | The legacy grid ends where the shorter dataset ends (`least(...)`). The county model's test year is complete: 2025-01-01 to 2025-12-31 |

## Other sources

| Source | Quirk | Fix |
|---|---|---|
| HRRR via Open-Meteo | Free tier counts ~26 "calls" per region-year (10 variables x 2-week units); 10,000/day | `ingest/fetch_weather.py` paces requests, resumes, retries with backoff |
| HRRR at one point per county | Storm winds are local: KSTL measured a 23.7 m/s gust on 2023-07-02 while HRRR at the county's point showed 5.8 | Keep Storm Events as an independent "storm happened" signal |
| HRRR hourly rain: ~1,000 region-hours over 100 mm, up to 340 mm (2024-05-07, Morgan Co., MO), mostly with light winds | Beyond any record here; inflates rain sums | The hourly table (`mart_study__region_1h`) treats over 100 mm in an hour as unknown |
| EAGLE-I coverage by region-year: 47 regions look untracked in 2018, 6 in 2019, Webster and McDonald Co., MO into 2020–2022 | Untracked years look calm | `mart_study__region_coverage`: tracked when the share of hours with anyone out is at least a fifth of the region's 75th-percentile year; the moving-window model drops the rest |
| NOAA Storm Events | Times in **local standard time all year** (`CZ_TIMEZONE` = `CST-6`, and `EST-5` in parts of IN/KY/TN, `MST-7` in western KS); `BEGIN_DATE_TIME` has a 2-digit year | Rebuild timestamps from `BEGIN_YEARMONTH/DAY/TIME`, subtract each report's own offset |
| NOAA Storm Events | Winter/wind events are filed by NWS **zone**, not county | NWS zone–county correlation file; zone events spread to every county in the zone |
| NLCD Tree Canopy (MRLC WCS) | GeoTIFF's nodata tag says **0**, which is a real value (0% canopy); 254 = no data | Read raw pixels, mask by shape ourselves (`rasterio.mask` dropped every 0 → farm counties read 45% instead of ~2%) |
| Census API | Now requires a key | Key-free table-based summary files (`acsdt5y2024-<table>.dat`) |
| Census ACS | A merged region's median year built can't be computed from county medians | Housing-weighted average of the two county medians (St. Louis only) |

## Tooling traps

- conda-forge and Homebrew builds of the DuckDB CLI **can't load official extensions** (e.g. the UI) — use the official build (`curl https://install.duckdb.org | sh`).
- conda-forge's Python DuckDB is 1.5.6, which **can't open files written by DuckDB 2.x** — this repo installs `duckdb==2.0.0` from PyPI.
- Only **one writer** can open a DuckDB file at a time; read-only connections also block writers. Close the UI / restart notebook kernels before `pixi run build`.
- `WHERE` runs **before** window functions — filter years *after* computing lags, or the first lags come out empty.
- DuckDB 2.x: the lambda arrow `x -> …` is deprecated (use `lambda x: …`); in Python, read each `execute()` result before running more SQL on the same connection.
- **DuckDB's `least()` / `greatest()` skip NULLs**: `least(100, NULL)` is 100, not NULL. That turned every blank outage count into "100% out" (tens of thousands of spurious events) until a test caught it — check `IS NULL` explicitly.
- **dbt-duckdb `external_location` goes through Python `str.format()`**: curly braces (`read_csv(types = {...})`) break it. Read as text and cast in staging.
- conda-forge `mlflow` pulls protobuf 7, which dbt-common rejects; Streamlit excludes pyarrow 25.0.0 (the installer silently fell back to Streamlit 1.8). Both come from PyPI in `pixi.toml`.

