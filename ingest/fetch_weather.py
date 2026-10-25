"""Hourly storm "ingredients" per region from NOAA's HRRR model, via Open-Meteo.

This is the free stand-in for WeatherNext in the weathernext-outage-forecasting
project: the same kinds of variables (surface wind and gusts, wind aloft for
shear, CAPE for updraft strength, precipitation, temperature, freezing level
for a hail proxy), from HRRR — NOAA's 3 km storm-resolving model.

Open-Meteo's Historical Forecast API stitches together the first hours of each
HRRR run, so this is "short-range forecast" weather: close to what happened,
not a 24–48 h-ahead forecast (see docs/decisions.md).

One CSV per region per year: data/raw/weather/hrrr/<region_fips>_<year>.csv.gz
Re-running skips files that exist, so it can be stopped and resumed any time.

Rate limits (free, non-commercial): 600 calls/min, 5,000/hour, 10,000/day,
where a call is up to 10 variables x 2 weeks — so one region-year = ~26 calls.
We pace requests to ~4,700 calls/hour and back off on HTTP 429.

Usage:
  pixi run fetch-weather              # default years (see YEARS)
  pixi run fetch-weather 2022 2023    # other years
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
REGIONS_CSV = Path("data/raw/geo/regions_mo_il.csv")
OUT_DIR = Path("data/raw/weather/hrrr")
YEARS = [2024, 2025]
VARIABLES = [                 # max 10 per call before it counts double
    "wind_gusts_10m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_speed_850hPa",      # low-level jet, ~1.5 km
    "wind_speed_500hPa",      # mid-level wind, ~5.6 km — with 10 m wind gives 0–6 km shear
    "wind_direction_500hPa",
    "cape",                   # convective energy: updraft-strength proxy
    "precipitation",
    "temperature_2m",
    "freezing_level_height",  # low freezing level + high CAPE = hail-prone
]
CALLS_PER_REQUEST = 365 / 14  # one year of data counts as ~26 calls
SECONDS_BETWEEN = 3600 * CALLS_PER_REQUEST / 4700


def fetch_one(lat, lon, year):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(VARIABLES),
        "models": "ncep_hrrr_conus",
        "wind_speed_unit": "ms",
        "timezone": "GMT",
    }
    failures = 0
    while True:
        try:
            r = requests.get(URL, params=params, timeout=120,
                             headers={"User-Agent": "storm-outage-risk (personal, non-commercial)"})
            if r.status_code == 429:                   # over a limit: wait, then retry
                print(f"  rate limited ({r.text[:120]}); sleeping 30 min", flush=True)
                time.sleep(1800)
                continue
            r.raise_for_status()
            return pd.DataFrame(r.json()["hourly"])
        except (requests.RequestException, ValueError, KeyError) as e:
            # network hiccup, 5xx, or a reply that isn't the JSON we expect:
            # back off 1, 2, 4 ... up to 30 minutes, then try again
            failures += 1
            wait = min(60 * 2 ** (failures - 1), 1800)
            print(f"  attempt {failures} failed ({type(e).__name__}: {str(e)[:100]}); retrying in {wait}s", flush=True)
            time.sleep(wait)


def main(years):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    regions = pd.read_csv(REGIONS_CSV, dtype={"region_fips": str})
    todo = [(row, y) for _, row in regions.iterrows() for y in years
            if not (OUT_DIR / f"{row.region_fips}_{y}.csv.gz").exists()]
    print(f"{len(todo)} region-years to download (~{len(todo) * SECONDS_BETWEEN / 3600:.1f} h at the paced rate)", flush=True)

    for i, (row, year) in enumerate(todo, 1):
        start = time.time()
        df = fetch_one(row.lat, row.lon, year)
        df.insert(0, "region_fips", row.region_fips)
        out = OUT_DIR / f"{row.region_fips}_{year}.csv.gz"
        df.to_csv(out.with_suffix(".tmp"), index=False, compression="gzip")
        out.with_suffix(".tmp").rename(out)            # only complete files get the real name
        print(f"[{i}/{len(todo)}] {row.region} ({row.region_fips}) {year}: {len(df)} hours", flush=True)
        time.sleep(max(0, SECONDS_BETWEEN - (time.time() - start)))


if __name__ == "__main__":
    main([int(y) for y in sys.argv[1:]] or YEARS)
