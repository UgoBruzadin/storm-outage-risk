"""HRRR forecasts as issued, per region, from the hrrrzarr archive on AWS (University of Utah).

fetch_weather.py stores the weather each hour turned out to be (Open-Meteo stitches the
first hour of each HRRR run). This stores what each hourly HRRR run *predicted* for the
hours after it was issued: the input a utility would actually have had when deciding.

For every run (one per hour) it reads the same storm ingredients as fetch_weather.py at
forecast hours 1-13, which covers every lead the moving-window model uses (decision at
the run's issue time + 2 h, window up to 6 + 6 hours later). The archive stores each
variable in 150 x 150-cell tiles of the 3 km grid holding every forecast hour; the study
regions fit in 4 of them, so a run is 44 tiles (~30 MB) read straight from S3 and reduced
to the cell nearest each region's point (the same points fetch_weather.py uses). Nothing
but the extracted points is written to disk.

One Parquet file per day of runs: data/raw/weather/hrrr_fcst/<YYYYMMDD>.parquet with
run (issue time, UTC), fhour, hour (= run + fhour), region_fips and the variables.
Re-running skips days already written. A run missing from the archive is skipped.

Usage:
  pixi run python -m ingest.fetch_hrrr_forecast 2025-01-01 2025-12-31
"""
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numcodecs
import numpy as np
import pandas as pd
import pyproj

BASE = "https://hrrrzarr.s3.amazonaws.com/sfc"
REGIONS_CSV = Path("data/raw/geo/regions_study.csv")
OUT_DIR = Path("data/raw/weather/hrrr_fcst")
FHOURS = range(1, 14)
TILE = 150
VARIABLES = {                 # our name: archive path (level/variable)
    "gust_ms": "surface/GUST",
    "u10": "10m_above_ground/UGRD",
    "v10": "10m_above_ground/VGRD",
    "u850": "850mb/UGRD",
    "v850": "850mb/VGRD",
    "u500": "500mb/UGRD",
    "v500": "500mb/VGRD",
    "cape_jkg": "surface/CAPE",
    "precip_mm": "surface/APCP_1hr_acc_fcst",   # the hour ending at the forecast hour
    "temp_k": "2m_above_ground/TMP",
    "freezing_level_m": "0C_isotherm/HGT",
}
# HRRR's Lambert conformal grid; the archive's x/y coordinates are in these metres
HRRR = pyproj.CRS.from_proj4("+proj=lcc +lat_0=38.5 +lon_0=-97.5 +lat_1=38.5 +lat_2=38.5 +R=6371229 +units=m")
X0, Y0, DX = -2697520.14252193, -1587306.15255666, 3000.0
BLOSC = numcodecs.Blosc()


def grid_points():
    """Each region's nearest grid cell, as (tile row, tile col, row in tile, col in tile)."""
    regions = pd.read_csv(REGIONS_CSV, dtype={"region_fips": str})
    x, y = pyproj.Transformer.from_crs("EPSG:4326", HRRR, always_xy=True).transform(
        regions.lon.to_numpy(), regions.lat.to_numpy())
    col = np.rint((x - X0) / DX).astype(int)
    row = np.rint((y - Y0) / DX).astype(int)
    return regions.region_fips.to_numpy(), row // TILE, col // TILE, row % TILE, col % TILE


def get(url, tries=5):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):            # not in the archive
                return None
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {err}")


def fetch_run(run, points, pool):
    """One run's forecast hours 1-13 at every region point, or None if the run is missing."""
    fips, trow, tcol, irow, icol = points
    tiles = sorted(set(zip(trow, tcol, strict=True)))
    stem = f"{BASE}/{run:%Y%m%d}/{run:%Y%m%d_%H}z_fcst.zarr"
    jobs = {(name, t): f"{stem}/{path}/{path.split('/')[0]}/{path.split('/')[1]}/0.{t[0]}.{t[1]}"
            for name, path in VARIABLES.items() for t in tiles}
    raw = dict(zip(jobs, pool.map(get, jobs.values()), strict=True))
    if any(v is None for v in raw.values()):
        return None
    out = {}
    for name in VARIABLES:
        values = np.full((len(FHOURS), len(fips)), np.nan, dtype="float32")
        for t in tiles:
            cube = np.frombuffer(BLOSC.decode(raw[(name, t)]), dtype="<f4").reshape(-1, TILE, TILE)
            here = (trow == t[0]) & (tcol == t[1])
            n = min(len(FHOURS), len(cube))           # a few runs store fewer hours: the rest stay unknown
            values[:n, here] = cube[:n][:, irow[here], icol[here]]   # index i = fhour i + 1
        values[values == -9999.0] = np.nan
        out[name] = values.ravel()
    df = pd.DataFrame(out)
    df.insert(0, "region_fips", np.tile(fips, len(FHOURS)))
    df.insert(0, "fhour", np.repeat(list(FHOURS), len(fips)).astype("int8"))
    df.insert(0, "run", run)
    df.insert(2, "hour", run + pd.to_timedelta(df.fhour.astype(int), unit="h"))
    return df


def main(start, end):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    points = grid_points()
    with ThreadPoolExecutor(max_workers=16) as pool:
        for day in pd.date_range(start, end, freq="D"):
            path = OUT_DIR / f"{day:%Y%m%d}.parquet"
            if path.exists():
                continue
            t0 = time.time()
            runs = [fetch_run(day + pd.Timedelta(hours=h), points, pool) for h in range(24)]
            found = [r for r in runs if r is not None]
            if found:
                df = pd.concat(found, ignore_index=True)
                df["temp_c"] = df.pop("temp_k") - 273.15
                df.to_parquet(path, index=False)
            print(f"{day:%Y-%m-%d}: {len(found)}/24 runs, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
