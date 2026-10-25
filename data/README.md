# data/

Not tracked by git (except this file). Everything here can be rebuilt from public sources.

```
data/
├── raw/
│   ├── eaglei/        eaglei_outages_2014.csv … _2025.csv, MCC.csv, coverage_history.csv, citation_*.txt
│   ├── noaa/          noaa_KSTL_2014.csv … _2025.csv
│   ├── weather/hrrr/  <region_fips>_<year>.csv.gz   (Open-Meteo HRRR)
│   ├── geo/           county shapes, tree canopy tiles + summary
│   ├── acs/           Census summary-file tables
│   └── storm_events/  NOAA Storm Events + NWS zone–county file
├── warehouse.duckdb   built by `pixi run build` (dbt)
├── mlflow.db, mlruns/ MLflow runs (`pixi run train`)
└── app/               small Parquet files for the dashboard (`pixi run export-app`)
```

## Getting the raw data

- **EAGLE-I outages** (~11 GB): manual download of the full dataset from the DOE/ORNL release on figshare (search "EAGLE-I recorded electricity outages"). Unzip into `data/raw/eaglei/`. Keep the `citation_*.txt` files — they're how to credit the data.
- **Everything else**: the `pixi run fetch-*` tasks — see `ingest/README.md`.

Currently `data/raw` is a symlink to the old sandbox repo — see [docs/working-on-this.md](../docs/working-on-this.md#where-the-data-lives).
