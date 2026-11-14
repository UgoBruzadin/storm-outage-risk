"""Turn the national HRRR GRIB extracts (fetch_hrrr_grib.py) into the study area's weather files.

The rest of the pipeline reads two weather inputs; this writes both, for the regions in
data/raw/geo/regions_study.csv, so nothing downstream changes:

  hourly     data/raw/weather/hrrr/<region_fips>_<year>.csv.gz, the columns fetch_weather.py gets from
             Open-Meteo: the weather each hour turned out to be, here forecast hour 1 of the run issued
             the hour before (Open-Meteo stitches the first hours of each run the same way).
             Wind as speed + direction; HRRR's winds are relative to its grid, so directions are turned
             by a fixed angle at each point, which leaves speeds and shear (a difference of two winds at
             the same point) unchanged.
  forecasts  data/raw/weather/hrrr_fcst/<YYYYMMDD>.parquet, fetch_hrrr_forecast.py's files, for the
             study regions only.

Usage:
  pixi run python -m ingest.grib_to_study hourly <grib dir> [<grib dir> ...]
  pixi run python -m ingest.grib_to_study forecasts <grib dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REGIONS_CSV = Path("data/raw/geo/regions_study.csv")
HOURLY_DIR = Path("data/raw/weather/hrrr")
FCST_DIR = Path("data/raw/weather/hrrr_fcst")


def study_fips():
    return pd.read_csv(REGIONS_CSV, dtype={"region_fips": str}).region_fips.tolist()


def read_day(path, fips, fhours=None):
    filters = [("region_fips", "in", fips)] + ([("fhour", "in", fhours)] if fhours else [])
    return pq.read_table(path, filters=filters).to_pandas()


def direction(u, v):
    """Where the wind blows from, in degrees."""
    return np.round((np.degrees(np.arctan2(-u, -v)) + 360) % 360)


def hourly(grib_dirs):
    """One calendar year at a time, so the whole country (3,108 regions) fits in memory: a day file holds the
    runs issued that day, whose forecast hour 1 runs to 00 UTC of the next day, so a year's hours come from the
    files of Dec 31 of the year before through Dec 31 of the year itself."""
    fips = study_fips()
    days = sorted({p for d in grib_dirs for p in Path(d).glob("*.parquet")}, key=lambda p: p.name)
    by_name = {}
    for p in days:                                   # a day in two folders (an overlap) is read from both
        by_name.setdefault(p.stem, []).append(p)
    years = sorted({int(s[:4]) for s in by_name})
    for y in years:
        files = [p for s, ps in by_name.items() if f"{y - 1}1231" <= s <= f"{y}1231" for p in ps]
        df = pd.concat([read_day(p, fips, [1]) for p in files], ignore_index=True)
        df = df[df.hour.dt.year == y]
        if len(df):
            write_hourly(df)


def write_hourly(df):
    df = df.drop_duplicates(["region_fips", "hour"]).sort_values(["region_fips", "hour"])
    out = pd.DataFrame({
        "region_fips": df.region_fips,
        "time": df.hour.dt.strftime("%Y-%m-%dT%H:%M"),
        "wind_gusts_10m": df.gust_ms.round(2),
        "wind_speed_10m": np.hypot(df.u10, df.v10).round(2),
        "wind_direction_10m": direction(df.u10, df.v10),
        "wind_speed_850hPa": np.hypot(df.u850, df.v850).round(2),
        "wind_speed_500hPa": np.hypot(df.u500, df.v500).round(2),
        "wind_direction_500hPa": direction(df.u500, df.v500),
        "cape": df.cape_jkg.round(1),
        "precipitation": df.precip_mm.round(2),
        "temperature_2m": df.temp_c.round(2),
        "freezing_level_height": df.freezing_level_m.round(1),
    })
    HOURLY_DIR.mkdir(parents=True, exist_ok=True)
    year = df.hour.dt.year
    for (region, y), part in out.groupby([df.region_fips, year]):
        part.to_csv(HOURLY_DIR / f"{region}_{y}.csv.gz", index=False)
    print(f"{out.region_fips.nunique()} regions, {out.time.min()} to {out.time.max()}, {len(out):,} hours -> "
          f"{HOURLY_DIR}")


def forecasts(grib_dir):
    fips = study_fips()
    FCST_DIR.mkdir(parents=True, exist_ok=True)
    days = sorted(Path(grib_dir).glob("*.parquet"))
    for p in days:
        read_day(p, fips).to_parquet(FCST_DIR / p.name, index=False)
    print(f"{len(days)} days, {len(fips)} regions -> {FCST_DIR}")


if __name__ == "__main__":
    {"hourly": lambda: hourly(sys.argv[2:]), "forecasts": lambda: forecasts(sys.argv[2])}[sys.argv[1]]()
