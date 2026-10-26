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

- **EAGLE-I outages** (~11 GB): download the full dataset (DOI [10.13139/ORNLNCCS/1975202](https://doi.org/10.13139/ORNLNCCS/1975202)) and unzip it into `data/raw/eaglei/`, keeping the `citation_*.txt` files.
- **Everything else**: the `pixi run fetch-*` tasks — see `ingest/README.md`.

