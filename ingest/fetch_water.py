"""Rivers and streams per region (USGS National Hydrography Dataset, through The National Map).

Asks the NHD map service for each region's rivers wide enough to be mapped as areas and for its stream lines (the
small-scale layer, so mainly the larger streams), simplified to about 50 m. Measures how much of the region lies near
one of those rivers and how dense its streams are.

Output: data/raw/place/water.csv
  water_share             share of the county outline that is water (Census land and water areas)
  river_near_share        share of the region within 1 km of a river mapped as an area
  stream_km_per_km2       length of mapped streams per km2 of land

Usage: pixi run fetch-water   (caches each region, so it can resume; needs fetch-counties)
"""
import json
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

URL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/{layer}/query"
AREA_LAYER, LINE_LAYER = 9, 4
RIVER = "FTYPE=460"                          # NHD feature type: stream or river
CACHE = Path("data/raw/place/nhd")
REGIONS = Path("data/raw/geo/regions_study.parquet")
OUT = Path("data/raw/place/water.csv")
CRS = 5070                                   # equal-area, in meters
NEAR_M = 1000
PAGE = 1000
PAUSE_S = 0.5


def page(layer, where, bounds, offset):
    params = {"where": where, "geometry": ",".join(map(str, bounds)), "geometryType": "esriGeometryEnvelope",
              "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "FTYPE",
              "maxAllowableOffset": 0.0005, "resultOffset": offset, "resultRecordCount": PAGE, "f": "geojson"}
    for attempt in range(5):
        time.sleep(PAUSE_S)
        try:
            r = requests.get(URL.format(layer=layer), params=params, timeout=300)
            if r.ok and "features" in r.json():
                return r.json()["features"]
        except (requests.RequestException, ValueError):
            pass
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"NHD query failed: layer {layer}, {bounds}, offset {offset}")


def features(name, fips, layer, where, bounds):
    path = CACHE / f"{fips}_{name}.geojson"
    if not path.exists():
        found, offset = [], 0
        while True:
            got = page(layer, where, bounds, offset)
            found += got
            if len(got) < PAGE:
                break
            offset += PAGE
        path.write_text(json.dumps({"type": "FeatureCollection", "features": found}))
    if not json.loads(path.read_text())["features"]:
        return None
    return gpd.read_file(path).set_crs(4326, allow_override=True).to_crs(CRS)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    regions = gpd.read_parquet(REGIONS)
    rows = []
    for i, r in enumerate(regions.itertuples(), 1):
        shape = gpd.GeoSeries([r.geometry], crs=4326).to_crs(CRS).iloc[0]
        rivers = features("rivers", r.region_fips, AREA_LAYER, RIVER, r.geometry.bounds)
        streams = features("streams", r.region_fips, LINE_LAYER, "1=1", r.geometry.bounds)
        near = 0.0
        if rivers is not None:
            near = rivers.geometry.buffer(0).union_all().buffer(NEAR_M).intersection(shape).area
        km = streams.clip(shape).length.sum() / 1000 if streams is not None else 0.0
        rows.append({"region_fips": r.region_fips, "water_share": max(0.0, 1 - r.land_m2 / shape.area),
                     "river_near_share": near / shape.area, "stream_km_per_km2": km / (r.land_m2 / 1e6)})
        if i % 25 == 0:
            print(f"{i}/{len(regions)}", flush=True)
    out = pd.DataFrame(rows).round(4)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions")


if __name__ == "__main__":
    main()
