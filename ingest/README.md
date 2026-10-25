# ingest/

Scripts that download raw data into `../data/raw/<source>/`. Each one skips files that already exist, so re-running is safe.

- `fetch_noaa.py` — NOAA hourly weather for the stations in `STATIONS` (`pixi run fetch-noaa`)
