"""Public road km per region, and how much of it runs under tree canopy (Census TIGER/Line 2023 + NLCD TCC 2021).

Distribution lines, the poles that storms knock down, mostly run along roads, and no public map of them exists,
so road km stand in for line km. Public roads only (MTFCC): S1100 primary, S1200 secondary, S1400 local streets.
A road on a county line is counted in both counties. A county whose 2023 file can't be downloaded comes from the
2024 or 2022 release instead (the file name says which).

Canopy along roads: each region's roads drawn onto its canopy tile from fetch_tree_canopy.py (~90 m pixels, every
pixel a road touches); treed = pixel canopy >= 50%, the same cut as canopy_dense_share.

Output: data/raw/place/roads.csv
  road_km, road_km_primary / _secondary / _local   public road length
  road_canopy_mean_pct                              average canopy under the roads
  road_treed_share, road_km_treed                   share and km of road under >= 50% canopy

Usage: pixi run python -m ingest.fetch_roads   (~210 MB of downloads per two states; needs fetch-tree-canopy first)
"""
import re
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
import requests
from rasterio.features import rasterize

BASE = "https://www2.census.gov/geo/tiger/TIGER2023/ROADS/"
CACHE = Path("data/raw/place/roads")
REGIONS = Path("data/raw/geo/regions_study.parquet")
TILES = Path("data/raw/geo/tcc_2021_tiles")
OUT = Path("data/raw/place/roads.csv")
PUBLIC = {"S1100": "primary", "S1200": "secondary", "S1400": "local"}


def download(states):
    CACHE.mkdir(parents=True, exist_ok=True)
    names = sorted(set(re.findall(r"tl_2023_\d{5}_roads\.zip", requests.get(BASE, timeout=60).text)))
    names = [n for n in names if n[8:10] in states]
    return [fetch(n) for n in names]


def fetch(name):
    """One county's roads, cached. If the 2023 file can't be had (the Census server persistently rejects a few, e.g.
    19057 Des Moines County, IA), the same county from the 2024 or 2022 release; the file name keeps the year."""
    for year in ("2023", "2024", "2022"):
        alt = name.replace("2023", year)
        if (CACHE / alt).exists():           # idempotent
            return CACHE / alt
    for year in ("2023", "2024", "2022"):
        alt = name.replace("2023", year)
        try:
            content = get_zip(BASE.replace("2023", year) + alt, tries=3 if year == "2023" else 5)
        except RuntimeError as e:
            print(e, flush=True)
            continue
        (CACHE / alt).write_bytes(content)
        time.sleep(0.5)                      # the Census server rejects fast runs of requests
        if year != "2023":
            print(f"{name}: used the {year} release", flush=True)
        return CACHE / alt
    raise RuntimeError(f"{name}: no release could be downloaded")


def get_zip(url, tries=5):
    """The Census server sometimes answers 200 with a "Request Rejected" HTML page: retry until it's a zip."""
    for attempt in range(tries):
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        if r.content[:4] == b"PK\x03\x04":
            return r.content
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"{url}: no zip after {tries} tries")


def main():
    regions = gpd.read_parquet(REGIONS)
    ids = set(regions.region_fips)
    merged = {m: r for r in ids if "+" in r for m in r.split("+")}      # St. Louis city + county
    parts = []
    for z in download({f[:2] for f in ids}):
        g = gpd.read_file(f"zip://{z}")
        g = g[g.MTFCC.isin(PUBLIC)].assign(region_fips=merged.get(z.name[8:13], z.name[8:13]))
        parts.append(g[["region_fips", "MTFCC", "geometry"]])
    roads = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    assert set(roads.region_fips) == ids, ids ^ set(roads.region_fips)
    roads["km"] = roads.to_crs(5070).length / 1000

    rows = []
    for fips, part in roads.groupby("region_fips"):
        row = {"region_fips": fips, "road_km": part.km.sum()}
        for code, name in PUBLIC.items():
            row[f"road_km_{name}"] = part.km[part.MTFCC == code].sum()
        with rasterio.open(TILES / f"{fips}.tif") as src:
            pixels = src.read(1)
            on_road = rasterize(((g, 1) for g in part.to_crs(src.crs).geometry), out_shape=pixels.shape,
                                transform=src.transform, all_touched=True, fill=0, dtype="uint8").astype(bool)
        values = pixels[on_road]
        values = values[values <= 100]           # 254/255 = no data
        row["road_canopy_mean_pct"] = float(values.mean())
        row["road_treed_share"] = float((values >= 50).mean())
        rows.append(row)
    out = pd.DataFrame(rows)
    out["road_km_treed"] = out.road_km * out.road_treed_share
    out.round(4).to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions, median {out.road_km.median():.0f} km of public road, "
          f"{out.road_treed_share.median():.0%} under dense canopy")


if __name__ == "__main__":
    main()
