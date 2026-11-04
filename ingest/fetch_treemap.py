"""Forest type and tree size per region (USFS TreeMap 2022, RDS-2025-0032).

TreeMap gives each 30 m forest pixel a measured Forest Inventory plot that matches it; the raster holds the plot's ID
and its attribute table holds the plot's forest type, tree size and dead trees. This counts each region's pixels by
plot and averages over its forest pixels. The tree table adds the share of live stems that are ash, which the emerald
ash borer has been killing in both states.

Output: data/raw/place/treemap.csv
  tm_forest_share              share of the region's pixels that TreeMap counts as forest (a check against canopy)
  tm_share_oak_hickory, tm_share_elm_ash_cottonwood, tm_share_softwood, tm_share_oak_pine, tm_share_maple_beech,
  tm_share_oak_gum_cypress     forest type, as a share of forest pixels (FIA FORTYPCD groups)
  tm_height_ft                 height of dominant trees
  tm_diameter_in               quadratic mean diameter
  tm_live_per_acre             live trees per acre
  tm_basal_area                live basal area, square feet per acre
  tm_dead_per_acre             standing dead trees per acre
  tm_dead_volume               standing dead volume, cubic feet per acre
  tm_ash_stem_share            share of live stems that are ash

Usage: pixi run fetch-treemap   (needs fetch-counties; download and extract RDS-2025-0032.zip into
data/raw/place/treemap, see data/README.md)
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

SRC = Path("data/raw/place/treemap/Data")
TIF = SRC / "TreeMap2022_CONUS.tif"
REGIONS = Path("data/raw/geo/regions_study.parquet")
OUT = Path("data/raw/place/treemap.csv")
TYPES = {"softwood": (100, 399), "oak_pine": (400, 499), "oak_hickory": (500, 599), "oak_gum_cypress": (600, 699),
         "elm_ash_cottonwood": (700, 799), "maple_beech": (800, 899)}
MEANS = {"tm_height_ft": "STANDHT", "tm_diameter_in": "QMD", "tm_live_per_acre": "TPA_LIVE",
         "tm_basal_area": "BALIVE", "tm_dead_per_acre": "TPA_DEAD", "tm_dead_volume": "VOLCFNET_D"}
ASH_GENUS = (540, 549)                       # FIA species codes for Fraxinus


def plot_table():
    """Per raster value: the plot's attributes and its live stems per acre, total and ash."""
    v = pyogrio.read_dataframe(TIF.with_suffix(".tif.vat.dbf"), read_geometry=False).rename(columns=str.upper)
    trees = pd.read_csv(SRC / "TreeMap2022_CONUS_Tree_Table.csv", usecols=["TM_ID", "STATUSCD", "SPCD", "TPA_UNADJ"])
    live = trees[trees.STATUSCD == 1]
    stems = live.groupby("TM_ID").TPA_UNADJ.sum().rename("stems")
    ash = live[live.SPCD.between(*ASH_GENUS)].groupby("TM_ID").TPA_UNADJ.sum().rename("ash")
    v = v.join(stems, on="TM_ID").join(ash, on="TM_ID").fillna({"stems": 0, "ash": 0})
    return v.set_index("VALUE")


def summarize(src, geometry, plots):
    window = from_bounds(*geometry.bounds, src.transform).round_offsets(op="floor").round_lengths(op="ceil")
    pixels = src.read(1, window=window)
    inside = geometry_mask([geometry], out_shape=pixels.shape, transform=src.window_transform(window), invert=True)
    values, counts = np.unique(pixels[inside], return_counts=True)
    keep = values != src.nodata
    p = plots.reindex(values[keep]).assign(n=counts[keep])
    forest = p.n.sum()
    row = {"tm_forest_share": forest / inside.sum()}
    for name, (low, high) in TYPES.items():
        row[f"tm_share_{name}"] = p.n[p.FORTYPCD.between(low, high)].sum() / forest
    for name, column in MEANS.items():
        row[name] = (p[column] * p.n).sum() / forest
    row["tm_ash_stem_share"] = (p.ash * p.n).sum() / (p.stems * p.n).sum()
    return row


def main():
    plots = plot_table()
    with rasterio.open(TIF) as src:
        regions = gpd.read_parquet(REGIONS).to_crs(src.crs)
        rows = []
        for i, r in enumerate(regions.itertuples(), 1):
            rows.append({"region_fips": r.region_fips, **summarize(src, r.geometry, plots)})
            if i % 25 == 0:
                print(f"{i}/{len(regions)}", flush=True)
    out = pd.DataFrame(rows).round(4)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions")


if __name__ == "__main__":
    main()
