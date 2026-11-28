# ⚡ Storm Outage Risk

> Which US counties will lose power in the next few hours, early enough to send repair crews?

Weather forecasts say when a storm will hit. They don't say where it will cut the power: the same storm can take out
2% of one county and 40% of the next. This project forecasts that, every hour, for every county in the lower 48 and
DC (3,108 county regions), using only public data and only what was known at the moment of the forecast.

**[Read the story](https://ugobruzadin.github.io/storm-outage-risk/)** (two minutes) ·
**[Read the write-up](https://ugobruzadin.github.io/storm-outage-risk/writeup/)** (methods and every result) ·
[Open the dashboard](https://storm-outage-risk.streamlit.app)

## What it predicts

Every hour, for every county: the chance that at least 5% of its customers lose power in the six hours starting two
hours later, in a county that had no outage in the 24 hours before. Two hours is the time it takes to get a crew in
place. "No outage before" matters: predicting that an outage already underway will continue is easy and inflates the
score about fourfold, so this project scores **new** outages only.

## Results on 2025

Settings and inputs were chosen on 2024. The final model was trained on 2020–2024 and scored on 2025, a year it
never trained on. Ranges are 95% over resampled 2025 storm days.

| What the forecast knows | PR-AUC (95% range) | × warnings + outlook |
|---|---|---|
| NWS warnings + SPC outlook alone (what utilities have today) | 0.022 (0.017–0.026) | 1× |
| Model, weather observed so far | 0.064 (0.055–0.074) | 3.0× (2.7–3.3×) |
| **Model + the last five HRRR forecast runs** | **0.102 (0.085–0.120)** | **4.7× (4.2–5.3×)** |
| Ceiling: knowing the window's actual weather | 0.115 (0.097–0.132) | 5.3× (4.8–5.9×) |

PR-AUC measures how well the county-hours followed by a new outage rank ahead of the rest. Random guessing scores
0.006, the share of county-hours followed by one. So "4.7×" means 4.7 times the official forecasts' PR-AUC, not 4.7
times as accurate.

What that means for alerts: give the model and the official forecasts the same budget, each alerting on its riskiest
0.75% of county-hours. The model catches 28.5% of 2025's 25,362 new outages in time; the official forecasts catch
12.6%. About one model alert in six is followed by a new outage. Most alerts are still false alarms and most outages
get no alert: it says where to look first, not what will happen.

**How clean is the test?** Not perfectly: one input (how long and how widely the wind blows) was first tried on
Missouri + Illinois 2025 data. The clean test is the live forecast below.

## Why the numbers can be trusted

- **Every input is known at the decision.** Weather so far, HRRR forecasts as they were issued (read from NOAA's
  archive of every hourly run), warnings in force, outages so far. The first version of this model "predicted"
  storms using the storm's own weather; [the write-up](https://ugobruzadin.github.io/storm-outage-risk/writeup/#question)
  shows how much that inflated the score. An [audit](docs/audit.md) recomputes every input from the raw tables to
  check that nothing sees the future.
- **Scored on new outages, on a later year, against the official forecasts**, with ranges from resampling whole
  storm days, not hours.
- **Public data has traps,** and 16 of them are written up with the code that fixes each: gaps that look like "no
  outages", one county's outages filed under its neighbour's code, a raster whose "no data" value meant "no trees".
  See [the pitfalls](https://ugobruzadin.github.io/storm-outage-risk/writeup/#pitfalls) and
  [data notes](docs/data-notes.md).

## Live forecast (beta)

| What | Status |
|---|---|
| **Missouri + Illinois blind test** | Live every hour since November 2026, from [storm-outage-live](https://github.com/UgoBruzadin/storm-outage-live). A frozen two-state model (`live-v1.1`), without current outage data: 2.2× warnings + outlook on 2025. Each forecast is saved before the weather happens and will be graded when EAGLE-I releases 2026's outage data. |
| **Lower 48 live model** | Trained, not live. Without current outage data (a live job can't get it) it scores 4.5× warnings + outlook on 2025 (4.0–5.1×). Its live feed isn't built yet. |

Experimental research forecast, not from any utility or the National Weather Service. Don't use it for safety
decisions.

## How it's built

```
ingest/ (Python)          dbt/ (SQL on DuckDB)                     ml/ (Python)                    site/ + app/
EAGLE-I outages, HRRR ──► staging → intermediate → marts     ──►  XGBoost, baselines, audit,  ──►  story page, write-up,
weather and forecasts,    61 tests; 162 M county-hours,            storm-day ranges,               Streamlit dashboard
NWS, SPC, place data      backward-looking inputs only             significance tests
```

| Layer | Tools |
|---|---|
| Environment | [pixi](https://pixi.sh), one lock file |
| Storage, SQL | [DuckDB](https://duckdb.org), dbt Core + dbt-duckdb |
| Geo | geopandas, rasterio |
| Models | XGBoost, scikit-learn, MLflow |
| Site, dashboard | D3, Streamlit, Plotly, Docker |
| Quality | pytest, ruff, GitHub Actions |

## Run it

```bash
pixi install
# EAGLE-I outages: manual download, see data/README.md
# Every other source: the pixi run fetch-* tasks, listed in ingest/README.md
pixi run build                  # dbt: every model and test
pixi run pipeline --smoke       # every step on Missouri + Illinois with 5 trees: minutes, a check before a long run
pixi run pipeline               # every experiment behind the site (about 20 hours for the lower 48)
pixi run app                    # dashboard at http://localhost:8501
```

`pixi run pipeline --list` shows every step; `docker compose up --build` runs the dashboard in a container.

## Where to read more

| You want | Read |
|---|---|
| The findings and how they were tested | [Write-up](https://ugobruzadin.github.io/storm-outage-risk/writeup/) |
| Every experiment, in order, with its result | [docs/experiments.md](docs/experiments.md) |
| Why each design choice was made | [docs/decisions.md](docs/decisions.md) |
| Every table and column | [docs/data-dictionary.md](docs/data-dictionary.md) |
| Data problems found and fixed | [docs/data-notes.md](docs/data-notes.md) |
| The look-ahead audit | [docs/audit.md](docs/audit.md) |
| Working on the code | [docs/development.md](docs/development.md) |

## Data sources

DOE / Oak Ridge National Laboratory EAGLE-I outage records
([doi:10.13139/ORNLNCCS/1975202](https://doi.org/10.13139/ORNLNCCS/1975202)); NOAA HRRR weather and forecast runs
(NOAA archive on AWS; Open-Meteo for the Missouri + Illinois live feed); NWS warnings and SPC outlooks via the Iowa
Environmental Mesonet; NOAA Storm Events; USFS / NLCD tree canopy; U.S. Census Bureau (ACS, TIGER roads, county
boundaries); USDA NRCS soil; FEMA flood zones; EIA-861 utilities. Full list with URLs:
[docs/data-dictionary.md](docs/data-dictionary.md#where-the-data-comes-from).

Ugo Bruzadin Nunes · MIT License
