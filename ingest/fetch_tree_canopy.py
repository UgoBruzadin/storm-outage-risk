"""Tree canopy cover per region (USFS / NLCD Tree Canopy Cover, 2021).

For each region, asks MRLC's map server (WCS) for just that region's
rectangle, at 1/3 resolution (~90 m instead of 30 m — county averages come
out the same, and downloads are 9x smaller), then summarizes the pixels that
fall inside the region's shape.

Pixel values are % canopy (0–100); 254/255 mean "no data". The file's own
nodata tag says 0, which is wrong (0 is a real "no trees" value), so we mask
by value instead.

Output: data/raw/geo/tree_canopy_2021.csv
  canopy_mean_pct     average canopy cover over the region's land
  canopy_dense_share  share of pixels with >= 50% canopy (forest-like)

Usage: pixi run fetch-tree-canopy   (~5 min; needs fetch-counties first)
"""
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
import requests
from rasterio.features import geometry_mask

WCS = "https://www.mrlc.gov/geoserver/ows"
COVERAGE = "mrlc_download__nlcd_tcc_conus_2021_v2021-4"
REGIONS = Path("data/raw/geo/regions_mo_il.parquet")
CACHE = Path("data/raw/geo/tcc_2021_tiles")
OUT = Path("data/raw/geo/tree_canopy_2021.csv")


def fetch_tile(region_fips, bounds):
    path = CACHE / f"{region_fips}.tif"
    if path.exists():                        # idempotent
        return path
    minx, miny, maxx, maxy = bounds
    params = {
        "service": "WCS", "version": "2.0.1", "request": "GetCoverage",
        "coverageId": COVERAGE, "format": "image/geotiff",
        "subsettingcrs": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "SCALEFACTOR": "0.3333",
    }
    # requests can't repeat a key in a dict, so the two subsets go in a list
    query = list(params.items()) + [("subset", f"Long({minx},{maxx})"), ("subset", f"Lat({miny},{maxy})")]
    for attempt in range(3):
        r = requests.get(WCS, params=query, timeout=300)
        if r.ok and r.content[:2] in (b"II", b"MM"):   # a real TIFF, not an XML error
            path.write_bytes(r.content)
            return path
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{region_fips}: WCS failed: {r.status_code} {r.text[:200]}")


def summarize(path, geometry):
    with rasterio.open(path) as src:
        # Read the raw pixels and draw the shape ourselves. rasterio.mask.mask()
        # reads with the file's nodata tag (0), which silently turns every
        # 0%-canopy pixel into "no data" and inflates the mean (farm counties
        # came out at 45% instead of ~2%).
        pixels = src.read(1)
        inside = geometry_mask([geometry], out_shape=pixels.shape, transform=src.transform, invert=True)
    values = pixels[inside]
    values = values[values <= 100]           # drop 254/255 = no data
    return {
        "canopy_mean_pct": round(float(values.mean()), 2),
        "canopy_dense_share": round(float((values >= 50).mean()), 4),
        "canopy_pixels": int(values.size),
    }


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    regions = gpd.read_parquet(REGIONS)
    rows = []
    for i, r in enumerate(regions.itertuples(), 1):
        path = fetch_tile(r.region_fips, r.geometry.bounds)
        rows.append({"region_fips": r.region_fips, **summarize(path, r.geometry)})
        if i % 25 == 0:
            print(f"{i}/{len(regions)}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions, canopy mean {out.canopy_mean_pct.min()}–{out.canopy_mean_pct.max()}%")


if __name__ == "__main__":
    main()
