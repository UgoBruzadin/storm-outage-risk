# data/

Not tracked by git (except this file). Everything here can be rebuilt from public sources.

```
data/
├── raw/
│   ├── eaglei/      eaglei_outages_2014.csv … _2025.csv, MCC.csv, coverage_history.csv, citation_*.txt
│   └── noaa/        noaa_KSTL_2014.csv … _2025.csv
└── warehouse.duckdb built by `pixi run build`
```

## Getting the raw data

- **EAGLE-I outages** (~11 GB): manual download of the full dataset from the DOE/ORNL release on figshare (search "EAGLE-I recorded electricity outages"). Unzip into `data/raw/eaglei/`. Keep the `citation_*.txt` files — they're how to credit the data.
- **NOAA hourly weather**: `pixi run fetch-noaa`.

Currently `data/raw` is a symlink to the old sandbox repo — see [docs/working-on-this.md](../docs/working-on-this.md#where-the-data-lives).
