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
| `fetch-treemap` | `fetch_treemap.py` | USFS TreeMap 2022 forest type and tree size (~5 GB download) | `place/treemap.csv` |
| `fetch-forest-age` | `fetch_forest_age.py` | USFS FIA stand age, surveys 2014–2019 | `place/forest_age.csv` |
| `fetch-soil` | `fetch_soil.py` | NRCS SSURGO soil, through Soil Data Access | `place/soil.csv` |
| `fetch-water` | `fetch_water.py` | USGS NHD rivers and streams | `place/water.csv` |
| `fetch-flood-zones` | `fetch_flood_zones.py` | FEMA flood zones (slow, resumable) | `place/flood_zones.csv` |
| `fetch-transmission` | `fetch_transmission.py` | HIFLD transmission lines | `place/transmission.csv` |
| `fetch-utilities` | `fetch_utilities.py` | EIA-861 utilities and reliability, 2015–2019 | `place/utilities.csv` |

EAGLE-I outages are a manual download — see `../data/README.md`.
