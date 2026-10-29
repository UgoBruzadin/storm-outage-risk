# ingest/

Scripts that download raw data into `../data/raw/<source>/`. Each skips files that already
exist, so re-running is safe. Run them with the pixi tasks:

| Task | Script | Source | Output |
|---|---|---|---|
| `fetch-noaa` | `fetch_noaa.py` | NOAA Global Hourly (KSTL airport), AWS mirror | `noaa/` |
| `fetch-counties` | `fetch_counties.py` | Census cartographic county boundaries | `geo/regions_study.*` (216 regions) |
| `fetch-weather` | `fetch_weather.py` | HRRR storm ingredients via Open-Meteo (rate-limited, ~a day) | `weather/hrrr/` |
| `fetch-hrrr-forecast` | `fetch_hrrr_forecast.py` | HRRR forecasts as issued (hourly runs, forecast hours 1–13) from the hrrrzarr archive on AWS; ~1 min per day of runs | `weather/hrrr_fcst/` |
| `fetch-tree-canopy` | `fetch_tree_canopy.py` | USFS/NLCD Tree Canopy Cover 2021 via MRLC WCS | `geo/tree_canopy_2021.csv` |
| `fetch-acs` | `fetch_acs.py` | Census ACS 2020–2024 summary files (no key needed) | `acs/` |
| `fetch-storm-events` | `fetch_storm_events.py` | NOAA Storm Events + NWS zone–county file | `storm_events/` |

EAGLE-I outages are a manual download — see `../data/README.md`.
