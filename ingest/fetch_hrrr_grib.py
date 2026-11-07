"""HRRR forecasts as issued, for every county in the lower 48, from NOAA's GRIB2 archive on AWS.

fetch_hrrr_forecast.py reads the hrrrzarr archive in map tiles, which is cheap for two states but would mean ~600 MB
per run for the whole country. This reads NOAA's own archive (noaa-hrrr-bdp-pds) instead: each forecast file has an
index (.idx) giving the byte range of every field, so only the 11 storm ingredients are downloaded, ~12.5 MB per
forecast hour for the whole grid. Same variables, forecast hours and output columns as fetch_hrrr_forecast.py, at
the same kind of point (fetch_counties.py's representative point), so the model code reads either.

Counties: every county in the lower 48 from the Census file fetch_counties.py downloads, St. Louis City + County
merged as there, cached in data/raw/geo/regions_conus.csv. --states keeps only some (e.g. --states MO,IL,IA,IN).

  --keep DIR   also save the downloaded fields, one small GRIB2 file per run and forecast hour
               (DIR/<YYYYMMDD>/hrrr.tHHz.fNN.grib2, ~12.5 MB each). Later runs read these instead of downloading,
               so new counties or a different point can be extracted without fetching again.
  --fhours     forecast hours to read (default 1-13, every lead the moving-window model uses; "1" for the
               near-actual weather of training years)
  --workers    runs decoded in parallel (default: CPU count - 2)

One Parquet file per day of runs: data/raw/weather/hrrr_grib/<YYYYMMDD>.parquet. Re-running skips days already
written; a run missing from the archive is skipped.

Usage:
  pixi run python -m ingest.fetch_hrrr_grib 2025-06-01 2025-06-07 [--states MO,IL] [--keep D:/hrrr]
"""
import argparse
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import rasterio
from rasterio.io import MemoryFile

BASE = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"
COUNTY_ZIP = Path("data/raw/geo/cb_2023_us_county_500k.zip")
REGIONS_CSV = Path("data/raw/geo/regions_conus.csv")
OUT_DIR = Path("data/raw/weather/hrrr_grib")
NOT_CONUS = {"02", "15", "60", "66", "69", "72", "78"}        # AK, HI and the territories: outside the HRRR grid
STL_PARTS = {"29189", "29510"}
VARIABLES = {                 # our name: the field's name and level in the .idx
    "gust_ms": "GUST:surface",
    "u10": "UGRD:10 m above ground",
    "v10": "VGRD:10 m above ground",
    "u850": "UGRD:850 mb",
    "v850": "VGRD:850 mb",
    "u500": "UGRD:500 mb",
    "v500": "VGRD:500 mb",
    "cape_jkg": "CAPE:surface",
    "precip_mm": "APCP:surface",   # the hour ending at the forecast hour (picked in fields())
    "temp_k": "TMP:2 m above ground",
    "freezing_level_m": "HGT:0C isotherm",
}
HRRR = pyproj.CRS.from_proj4("+proj=lcc +lat_0=38.5 +lon_0=-97.5 +lat_1=38.5 +lat_2=38.5 +R=6371229 +units=m")
LEFT, TOP, DX = -2699020.14252193, 1588193.84744334, 3000.0      # the grid's outer corner, as GDAL reads it


def conus_regions():
    """Every lower-48 county as a region, with fetch_counties.py's weather point."""
    if REGIONS_CSV.exists():
        return pd.read_csv(REGIONS_CSV, dtype={"region_fips": str, "state_fips": str})
    shp = gpd.read_file(f"zip://{COUNTY_ZIP}")
    counties = shp[~shp.STATEFP.isin(NOT_CONUS)].copy()
    counties["region_fips"] = counties.GEOID.where(~counties.GEOID.isin(STL_PARTS), "29189+29510")
    counties["region"] = counties.NAME.where(~counties.GEOID.isin(STL_PARTS), "St. Louis City + County")
    regions = counties.dissolve(by="region_fips", aggfunc={"region": "first", "STATEFP": "first",
                                                            "STUSPS": "first"}).reset_index()
    points = regions.to_crs("EPSG:5070").representative_point().to_crs("EPSG:4326")
    regions = pd.DataFrame({"region_fips": regions.region_fips, "region": regions.region,
                            "state_fips": regions.STATEFP, "state": regions.STUSPS,
                            "lat": points.y.round(4).to_numpy(), "lon": points.x.round(4).to_numpy()})
    regions.to_csv(REGIONS_CSV, index=False)
    return regions


def grid_points(regions):
    """Each region's grid cell, as (row, col) counted from the grid's north-west corner."""
    x, y = pyproj.Transformer.from_crs("EPSG:4326", HRRR, always_xy=True).transform(
        regions.lon.to_numpy(), regions.lat.to_numpy())
    return np.floor((TOP - y) / DX).astype(int), np.floor((x - LEFT) / DX).astype(int)


def get(url, byte_range=None, tries=9):
    headers = {"Range": f"bytes={byte_range[0]}-{'' if byte_range[1] is None else byte_range[1]}"} if byte_range else {}
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):            # not in the archive
                return None
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        time.sleep(min(2 ** attempt, 60))      # ~4 min in all: rides out a dropped connection
    raise RuntimeError(f"{url}: {err}")


def fields(idx, fhour):
    """Byte ranges of our fields in one forecast file, from its .idx, in file order."""
    lines = [line.split(":") for line in idx.decode().splitlines()]
    out = {}
    for i, parts in enumerate(lines):
        what, when = ":".join(parts[3:5]), parts[5]
        for name, wanted in VARIABLES.items():
            if what != wanted:
                continue
            if name == "precip_mm" and when != f"{fhour - 1}-{fhour} hour acc fcst":
                continue                        # skip the total since the run started
            end = int(lines[i + 1][1]) - 1 if i + 1 < len(lines) else None     # None: to the file's end
            out[name] = (int(parts[1]), end)
    return out


def fetch_file(run, fhour, keep, pool):
    """One forecast hour's fields as GRIB2 bytes (from the --keep copy if there is one), or None."""
    saved = keep / f"{run:%Y%m%d}" / f"hrrr.t{run:%H}z.f{fhour:02d}.grib2" if keep else None
    if saved and saved.exists():
        return saved.read_bytes()
    url = f"{BASE}/hrrr.{run:%Y%m%d}/conus/hrrr.t{run:%H}z.wrfsfcf{fhour:02d}.grib2"
    idx = get(url + ".idx")
    if idx is None:
        return None
    ranges = fields(idx, fhour)
    if len(ranges) < len(VARIABLES):
        return None
    parts = list(pool.map(lambda r: get(url, r), ranges.values()))
    if any(p is None for p in parts):
        return None
    data = b"".join(parts)
    if saved:
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.with_suffix(".part").write_bytes(data)
        saved.with_suffix(".part").replace(saved)          # never leave a half-written file behind
    return data


def fetch_run(run, fhours, rows, cols, fips, keep):
    """One run's forecast hours at every region point, or None if the run is missing."""
    frames = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for fhour in fhours:
            data = fetch_file(run, fhour, keep, pool)
            if data is None:
                return None
            out = {}
            # GDAL converts temperatures to Celsius unless told not to; keep the archive's units
            with rasterio.Env(GRIB_NORMALIZE_UNITS="NO"), MemoryFile(data) as mem, mem.open() as src:
                for band in range(1, src.count + 1):
                    name = band_name(src.tags(band))
                    if name:
                        out[name] = src.read(band)[rows, cols].astype("float32")
            if len(out) < len(VARIABLES):
                return None
            df = pd.DataFrame(out)[list(VARIABLES)]
            df.insert(0, "region_fips", fips)
            df.insert(0, "fhour", np.int8(fhour))
            frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "run", run)
    df.insert(2, "hour", run + pd.to_timedelta(df.fhour.astype(int), unit="h"))
    return df


ELEMENTS = {("GUST", "0-SFC"): "gust_ms", ("UGRD", "10-HTGL"): "u10", ("VGRD", "10-HTGL"): "v10",
            ("UGRD", "85000-ISBL"): "u850", ("VGRD", "85000-ISBL"): "v850", ("UGRD", "50000-ISBL"): "u500",
            ("VGRD", "50000-ISBL"): "v500", ("CAPE", "0-SFC"): "cape_jkg", ("TMP", "2-HTGL"): "temp_k",
            ("HGT", "0-0DEG"): "freezing_level_m"}     # GDAL's (GRIB_ELEMENT, GRIB_SHORT_NAME) for each field


def band_name(tags):
    """Which of our variables a decoded band is, from GDAL's GRIB tags."""
    if tags["GRIB_ELEMENT"].startswith("APCP"):
        return "precip_mm"                      # fields() already kept only the 1-hour total
    return ELEMENTS.get((tags["GRIB_ELEMENT"], tags["GRIB_SHORT_NAME"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start")
    parser.add_argument("end")
    parser.add_argument("--states", help="comma-separated postal codes; default: the lower 48")
    parser.add_argument("--keep", type=Path, help="also save the downloaded fields here")
    parser.add_argument("--fhours", default="1-13", help='e.g. "1-13" or "1"')
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    lo, _, hi = args.fhours.partition("-")
    fhours = list(range(int(lo), int(hi or lo) + 1))
    regions = conus_regions()
    if args.states:
        regions = regions[regions.state.isin(args.states.upper().split(","))]
    rows, cols = grid_points(regions)
    fips = regions.region_fips.to_numpy()
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"{len(regions):,} regions, forecast hours {fhours[0]}-{fhours[-1]}, {args.workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as procs:
        for day in pd.date_range(args.start, args.end, freq="D"):
            path = args.out / f"{day:%Y%m%d}.parquet"
            if path.exists():
                continue
            t0 = time.time()
            runs = [day + pd.Timedelta(hours=h) for h in range(24)]
            found = [r for r in procs.map(fetch_run, runs, *[[x] * 24 for x in (fhours, rows, cols, fips,
                                                                                   args.keep)])
                     if r is not None]
            if found:
                df = pd.concat(found, ignore_index=True)
                df["temp_c"] = df.pop("temp_k") - 273.15
                df.to_parquet(path, index=False)
            print(f"{day:%Y-%m-%d}: {len(found)}/24 runs, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
