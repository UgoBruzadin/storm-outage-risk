"""HRRR forecasts as issued, summarized over each county's whole area (docs/experiments.md, E40-E42).

fetch_hrrr_forecast.py keeps one grid cell per county (the one nearest its center point), so a storm that crosses
the edge of a county can miss it. This version reads the same hourly runs (forecast hours 1-13, the 4 map tiles
that cover the study area, hrrrzarr archive on AWS) and keeps, per county and forecast hour:

  point values    the same 11 variables as fetch_hrrr_forecast.py, at the same cell (for continuity)
  area summaries  over every 3 km cell inside the county: the strongest gust and hourly max wind, the share of the
                  county with gusts >= 20 m/s, the highest storm energy (CAPE), the heaviest hourly rain and the share
                  with >= 10 mm, simulated radar (composite reflectivity: max, share >= 45 dBZ), storm-column ice
                  (VIL, a hail signal) and lightning (max, share of cells with any)

Cells are assigned to counties once, by their centers (data/raw/geo/regions_study.parquet), and cached.
One Parquet file per day of runs: data/raw/weather/hrrr_fcst_area/<YYYYMMDD>.parquet. Re-running skips days
already written; a run missing from the archive is skipped.

Usage:
  pixi run python -m ingest.fetch_hrrr_forecast_area 2019-12-31 2025-12-31
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj

from ingest.fetch_hrrr_forecast import BASE, BLOSC, DX, FHOURS, HRRR, TILE, X0, Y0, get, grid_points

OUT_DIR = Path("data/raw/weather/hrrr_fcst_area")
MASK = Path("data/raw/weather/hrrr_county_cells.parquet")
TILES = [(3, 6), (3, 7), (4, 6), (4, 7)]                 # (tile row, tile col): the study area
ROW0, COL0 = 3 * TILE, 6 * TILE                          # the 300 x 300 block they form starts here
VARIABLES = {                                            # our name: archive path (level/variable)
    "gust_ms": "surface/GUST",
    "u10": "10m_above_ground/UGRD",
    "v10": "10m_above_ground/VGRD",
    "u850": "850mb/UGRD",
    "v850": "850mb/VGRD",
    "u500": "500mb/UGRD",
    "v500": "500mb/VGRD",
    "cape_jkg": "surface/CAPE",
    "precip_mm": "surface/APCP_1hr_acc_fcst",
    "temp_k": "2m_above_ground/TMP",
    "freezing_level_m": "0C_isotherm/HGT",
    "wind1h_ms": "10m_above_ground/WIND_1hr_max_fcst",  # max 10 m wind during the hour
    "refc_dbz": "entire_atmosphere/REFC",                 # simulated composite radar reflectivity
    "vil_kgm2": "entire_atmosphere/VIL",                  # vertically integrated liquid (hail signal)
    "ltng": "entire_atmosphere/LTNG",                     # lightning threat
}
OPTIONAL = {"wind1h_ms", "refc_dbz", "vil_kgm2", "ltng"}      # absent from some runs (e.g. lightning): left unknown
POINT = ["gust_ms", "u10", "v10", "u850", "v850", "u500", "v500", "cape_jkg", "precip_mm", "temp_k",
         "freezing_level_m"]
AREA = {  # column: (variable, statistic, threshold for shares)
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


def county_cells():
    """Every grid cell of the 300 x 300 block whose center falls in a study region: (region, row, col)."""
    if MASK.exists():
        return pd.read_parquet(MASK)
    rows, cols = np.meshgrid(np.arange(ROW0, ROW0 + 2 * TILE), np.arange(COL0, COL0 + 2 * TILE), indexing="ij")
    lon, lat = pyproj.Transformer.from_crs(HRRR, "EPSG:4326", always_xy=True).transform(
        X0 + cols.ravel() * DX, Y0 + rows.ravel() * DX)
    cells = gpd.GeoDataFrame({"row": rows.ravel() - ROW0, "col": cols.ravel() - COL0},
                             geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326")
    regions = gpd.read_parquet("data/raw/geo/regions_study.parquet")[["region_fips", "geometry"]].to_crs("EPSG:4326")
    hit = gpd.sjoin(cells, regions, predicate="within")[["region_fips", "row", "col"]].reset_index(drop=True)
    MASK.parent.mkdir(parents=True, exist_ok=True)
    hit.to_parquet(MASK, index=False)
    return hit


def fetch_run(run, points, mask, pool):
    """One run's forecast hours 1-13: point values and county-area summaries, or None if the run is missing."""
    fips, trow, tcol, irow, icol = points
    prow, pcol = trow * TILE + irow - ROW0, tcol * TILE + icol - COL0        # the point cell in the block
    stem = f"{BASE}/{run:%Y%m%d}/{run:%Y%m%d_%H}z_fcst.zarr"
    jobs = {(name, t): f"{stem}/{path}/{path.split('/')[0]}/{path.split('/')[1]}/0.{t[0]}.{t[1]}"
            for name, path in VARIABLES.items() for t in TILES}
    raw = dict(zip(jobs, pool.map(get, jobs.values()), strict=True))
    if any(v is None for (name, _), v in raw.items() if name not in OPTIONAL):
        return None                                        # a core variable is missing: skip the run
    n_fh = len(FHOURS)
    block = {}
    for name in VARIABLES:
        cube = np.full((n_fh, 2 * TILE, 2 * TILE), np.nan, dtype="float32")
        for t in TILES:
            if raw[(name, t)] is None:                     # an optional field this run doesn't have
                continue
            c = np.frombuffer(BLOSC.decode(raw[(name, t)]), dtype="<f4").reshape(-1, TILE, TILE)
            n = min(n_fh, len(c))                             # a few runs store fewer hours: the rest stay unknown
            r0, c0 = (t[0] - 3) * TILE, (t[1] - 6) * TILE
            cube[:n, r0:r0 + TILE, c0:c0 + TILE] = c[:n]
        cube[cube == -9999.0] = np.nan
        block[name] = cube
    out = {name: block[name][:, prow, pcol].ravel() for name in POINT}      # fhour-major, region-minor
    # area summaries: cells sorted by region, reduced per region in one pass per forecast hour
    order = np.argsort(mask.region_idx.to_numpy(), kind="stable")
    region_idx = mask.region_idx.to_numpy()[order]
    cell_r, cell_c = mask.row.to_numpy()[order], mask.col.to_numpy()[order]
    starts = np.r_[0, np.flatnonzero(np.diff(region_idx)) + 1]
    counts = np.diff(np.r_[starts, len(region_idx)])
    present = region_idx[starts]                                            # regions that have cells
    for col, (var, stat, thr) in AREA.items():
        values = np.full((n_fh, len(fips)), np.nan, dtype="float32")
        for fh in range(n_fh):
            v = block[var][fh, cell_r, cell_c]
            if stat == "max":
                s = np.fmax.reduceat(v, starts)
            elif stat == "mean":
                s = np.add.reduceat(np.nan_to_num(v), starts) / counts
            elif np.isnan(v).all():                        # field missing in this run: share unknown, not 0
                s = np.full(len(starts), np.nan, dtype="float32")
            else:
                s = np.add.reduceat((np.nan_to_num(v) >= thr).astype("float32"), starts) / counts
            values[fh, present] = s
        out[col] = values.ravel()
    df = pd.DataFrame(out)
    df.insert(0, "region_fips", np.tile(fips, n_fh))
    df.insert(0, "fhour", np.repeat(list(FHOURS), len(fips)).astype("int8"))
    df.insert(0, "run", run)
    df.insert(2, "hour", run + pd.to_timedelta(df.fhour.astype(int), unit="h"))
    return df


def main(start, end):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    points = grid_points()
    mask = county_cells()
    mask["region_idx"] = mask.region_fips.map({f: i for i, f in enumerate(points[0])})
    mask = mask.dropna(subset=["region_idx"]).astype({"region_idx": int})
    with ThreadPoolExecutor(max_workers=16) as pool:
        for day in pd.date_range(start, end, freq="D"):
            path = OUT_DIR / f"{day:%Y%m%d}.parquet"
            if path.exists():
                continue
            t0 = time.time()
            runs = [fetch_run(day + pd.Timedelta(hours=h), points, mask, pool) for h in range(24)]
            found = [r for r in runs if r is not None]
            if found:
                df = pd.concat(found, ignore_index=True)
                df["temp_c"] = df.pop("temp_k") - 273.15
                df.to_parquet(path, index=False)
            print(f"{day:%Y-%m-%d}: {len(found)}/24 runs, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
