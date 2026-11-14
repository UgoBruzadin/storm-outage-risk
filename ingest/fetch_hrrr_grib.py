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
import http.client
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
# --area: the extra fields and county-wide summaries of fetch_hrrr_forecast_area.py (E40-E42), for every county
AREA_DIR = Path("data/raw/weather/hrrr_grib_area")
MASK = Path("data/raw/weather/hrrr_conus_county_cells.parquet")
EXTRA = {                     # optional fields: some runs lack them (e.g. lightning), left unknown then
    "wind1h_ms": "WIND:10 m above ground",          # max 10 m wind during the hour (picked in fields())
    "refc_dbz": "REFC:entire atmosphere",           # simulated composite radar reflectivity
    "vil_kgm2": "VIL:entire atmosphere",            # vertically integrated liquid (hail signal)
    "ltng": "LTNG:entire atmosphere",               # lightning threat
}
AREA = {  # column: (variable, statistic, threshold for shares), as fetch_hrrr_forecast_area.py
    "area_gust_max": ("gust_ms", "max", None),
    "area_gust_mean": ("gust_ms", "mean", None),
    "area_gust_share20": ("gust_ms", "share", 20.0),
    "area_wind1h_max": ("wind1h_ms", "max", None),
    "area_wind1h_share18": ("wind1h_ms", "share", 18.0),
    "area_cape_max": ("cape_jkg", "max", None),
    "area_precip_max": ("precip_mm", "max", None),
    "area_precip_share10": ("precip_mm", "share", 10.0),
    "area_refc_max": ("refc_dbz", "max", None),
    "area_refc_share45": ("refc_dbz", "share", 45.0),
    "area_vil_max": ("vil_kgm2", "max", None),
    "area_ltng_max": ("ltng", "max", None),
    "area_ltng_share": ("ltng", "share", 0.01),
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


def county_cells(regions):
    """Every HRRR grid cell whose center falls inside a region: (region_idx, row, col), sorted by region, cached.
    region_idx indexes `regions` (conus_regions' order)."""
    if MASK.exists():                           # every lower-48 county's cells: depends only on the county file
        cells = pd.read_parquet(MASK)
        cells["region_idx"] = cells.region_fips.map({f: i for i, f in enumerate(regions.region_fips)})
        return cells.dropna(subset=["region_idx"]).astype({"region_idx": int}).sort_values(
            "region_idx", kind="stable").reset_index(drop=True)
    shp = gpd.read_file(f"zip://{COUNTY_ZIP}")
    shp = shp[~shp.STATEFP.isin(NOT_CONUS)].copy()
    shp["region_fips"] = shp.GEOID.where(~shp.GEOID.isin(STL_PARTS), "29189+29510")
    shapes = shp.dissolve(by="region_fips").reset_index()[["region_fips", "geometry"]].to_crs(HRRR)
    rows, cols = np.meshgrid(np.arange(1059), np.arange(1799), indexing="ij")
    centers = gpd.GeoDataFrame({"row": rows.ravel().astype("int16"), "col": cols.ravel().astype("int16")},
                               geometry=gpd.points_from_xy(LEFT + (cols.ravel() + 0.5) * DX,
                                                           TOP - (rows.ravel() + 0.5) * DX), crs=HRRR)
    hit = gpd.sjoin(centers, shapes, predicate="within")[["region_fips", "row", "col"]].reset_index(drop=True)
    MASK.parent.mkdir(parents=True, exist_ok=True)
    hit.to_parquet(MASK, index=False)
    print(f"county cells: {len(hit):,} cells in {hit.region_fips.nunique():,} regions -> {MASK}", flush=True)
    return county_cells(regions)


def area_summaries(block, cells, n_regions):
    """fetch_hrrr_forecast_area.py's county-wide statistics for one forecast hour: {column: values per region}.
    block: {variable: 2-D grid}; cells: county_cells(); regions without a cell stay NaN."""
    region_idx = cells.region_idx.to_numpy()
    r, c = cells.row.to_numpy(), cells.col.to_numpy()
    starts = np.r_[0, np.flatnonzero(np.diff(region_idx)) + 1]
    counts = np.diff(np.r_[starts, len(region_idx)])
    present = region_idx[starts]
    out = {}
    for col, (var, stat, thr) in AREA.items():
        values = np.full(n_regions, np.nan, dtype="float32")
        grid = block.get(var)
        if grid is not None:
            v = grid[r, c]
            if stat == "max":
                s = np.fmax.reduceat(v, starts)
            elif stat == "mean":
                s = np.add.reduceat(np.nan_to_num(v), starts) / counts
            elif np.isnan(v).all():
                s = np.full(len(starts), np.nan, dtype="float32")
            else:
                s = np.add.reduceat((np.nan_to_num(v) >= thr).astype("float32"), starts) / counts
            values[present] = s
        out[col] = values
    return out


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
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as e:
            # HTTPException: a connection dropped mid-read (IncompleteRead)
            err = e
        time.sleep(min(2 ** attempt, 60))      # ~4 min in all: rides out a dropped connection
    raise RuntimeError(f"{url}: {err}")


def fields(idx, fhour, area=False):
    """Byte ranges of our fields in one forecast file, from its .idx, in file order (with area: EXTRA too)."""
    lines = [line.split(":") for line in idx.decode().splitlines()]
    wanted_fields = VARIABLES | (EXTRA if area else {})
    out = {}
    for i, parts in enumerate(lines):
        what, when = ":".join(parts[3:5]), parts[5]
        for name, wanted in wanted_fields.items():
            if what != wanted:
                continue
            if name == "precip_mm" and when != f"{fhour - 1}-{fhour} hour acc fcst":
                continue                        # skip the total since the run started
            if name == "wind1h_ms" and when != f"{fhour - 1}-{fhour} hour max fcst":
                continue                        # the max over the hour, not the instantaneous wind
            end = int(lines[i + 1][1]) - 1 if i + 1 < len(lines) else None     # None: to the file's end
            out[name] = (int(parts[1]), end)
    return out


def fetch_file(run, fhour, keep, pool, area=False):
    """One forecast hour's fields as GRIB2 bytes (from the --keep copy if there is one), or None."""
    saved = keep / f"{run:%Y%m%d}" / f"hrrr.t{run:%H}z.f{fhour:02d}{'.area' if area else ''}.grib2" if keep else None
    if saved and saved.exists():
        return saved.read_bytes()
    url = f"{BASE}/hrrr.{run:%Y%m%d}/conus/hrrr.t{run:%H}z.wrfsfcf{fhour:02d}.grib2"
    idx = get(url + ".idx")
    if idx is None:
        return None
    ranges = fields(idx, fhour, area)
    if not set(VARIABLES) <= set(ranges):       # a core field is missing: skip the run (extras may be absent)
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


_CELLS = None                 # county_cells(), handed to each worker process once (not with every run)


def _init_worker(cells):
    global _CELLS
    _CELLS = cells


def fetch_run(run, fhours, rows, cols, fips, keep, area=False):
    """One run's forecast hours at every region point, or None if the run is missing. With area:
    (points, points + county-wide summaries over _CELLS); the grid is read once for both."""
    cells = _CELLS if area else None
    frames, area_frames = [], []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for fhour in fhours:
            data = fetch_file(run, fhour, keep, pool, area=cells is not None)
            if data is None:
                return None
            out, block = {}, {}
            # GDAL converts temperatures to Celsius unless told not to; keep the archive's units
            with rasterio.Env(GRIB_NORMALIZE_UNITS="NO"), MemoryFile(data) as mem, mem.open() as src:
                for band in range(1, src.count + 1):
                    name = band_name(src.tags(band))
                    if not name:
                        continue
                    grid = src.read(band).astype("float32")
                    if name in VARIABLES:
                        out[name] = grid[rows, cols]
                    if cells is not None:
                        block[name] = grid
            if not set(VARIABLES) <= set(out):
                return None
            df = pd.DataFrame(out)[list(VARIABLES)]
            df.insert(0, "region_fips", fips)
            df.insert(0, "fhour", np.int8(fhour))
            frames.append(df)
            if cells is not None:
                area_frames.append(df.assign(**area_summaries(block, cells, len(fips))))
    stamp = []
    for parts in (frames, area_frames):
        if not parts:
            stamp.append(None)
            continue
        d = pd.concat(parts, ignore_index=True)
        d.insert(0, "run", run)
        d.insert(2, "hour", run + pd.to_timedelta(d.fhour.astype(int), unit="h"))
        stamp.append(d)
    return stamp[0] if cells is None else tuple(stamp)


ELEMENTS = {("GUST", "0-SFC"): "gust_ms", ("UGRD", "10-HTGL"): "u10", ("VGRD", "10-HTGL"): "v10",
            ("UGRD", "85000-ISBL"): "u850", ("VGRD", "85000-ISBL"): "v850", ("UGRD", "50000-ISBL"): "u500",
            ("VGRD", "50000-ISBL"): "v500", ("CAPE", "0-SFC"): "cape_jkg", ("TMP", "2-HTGL"): "temp_k",
            ("HGT", "0-0DEG"): "freezing_level_m",     # GDAL's (GRIB_ELEMENT, GRIB_SHORT_NAME) for each field
            ("WIND", "10-HTGL"): "wind1h_ms", ("REFC", "0-EATM"): "refc_dbz", ("VERIL", "0-EATM"): "vil_kgm2",
            ("LTNG", "0-EATM"): "ltng"}                # --area's extra fields


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
    parser.add_argument("--area", action="store_true",
                        help=f"also county-wide summaries and E41's fields -> {AREA_DIR}/<YYYYMMDD>.parquet "
                             "(fetch_hrrr_forecast_area.py's columns); days whose point file exists get only those")
    parser.add_argument("--area-out", type=Path, default=AREA_DIR, help="where --area writes")
    args = parser.parse_args()
    lo, _, hi = args.fhours.partition("-")
    fhours = list(range(int(lo), int(hi or lo) + 1))
    regions = conus_regions()
    if args.states:
        regions = regions[regions.state.isin(args.states.upper().split(","))].reset_index(drop=True)
    rows, cols = grid_points(regions)
    fips = regions.region_fips.to_numpy()
    cells = county_cells(regions) if args.area else None
    args.out.mkdir(parents=True, exist_ok=True)
    args.area_out.mkdir(parents=True, exist_ok=True)
    print(f"{len(regions):,} regions, forecast hours {fhours[0]}-{fhours[-1]}, {args.workers} workers"
          f"{', with county-wide summaries' if args.area else ''}", flush=True)

    def save(frames, path):
        df = pd.concat(frames, ignore_index=True)
        df["temp_c"] = df.pop("temp_k") - 273.15
        df.to_parquet(path.with_suffix(".part"), index=False)
        path.with_suffix(".part").replace(path)                   # never leave a half-written day behind

    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker, initargs=(cells,)) as procs:
        for day in pd.date_range(args.start, args.end, freq="D"):
            path, area_path = args.out / f"{day:%Y%m%d}.parquet", args.area_out / f"{day:%Y%m%d}.parquet"
            if path.exists() and (not args.area or area_path.exists()):
                continue
            t0 = time.time()
            runs = [day + pd.Timedelta(hours=h) for h in range(24)]
            found = [r for r in procs.map(fetch_run, runs, *[[x] * 24 for x in (fhours, rows, cols, fips,
                                                                                   args.keep, args.area)])
                     if r is not None]
            if found and args.area:
                if not path.exists():
                    save([p for p, _ in found], path)
                save([a for _, a in found], area_path)
            elif found:
                save(found, path)
            print(f"{day:%Y-%m-%d}: {len(found)}/24 runs, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
