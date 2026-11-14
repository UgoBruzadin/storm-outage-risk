"""FEMA flood zones per region (National Flood Hazard Layer).

Asks FEMA's map service for each county's Special Flood Hazard Areas (the 1% annual chance zones), simplified to about
50 m, and measures the share of the county they cover. A county with no flood zones inside it is left blank rather than
zero: it may have no digital map, which isn't the same as no flood risk. The query box can also catch a neighbour's
zones, so this looks inside the outline. A county mapped only in part still counts, so low values may mean less mapping.

Output: data/raw/place/flood_zones.csv
  flood_zone_share    share of the region inside a Special Flood Hazard Area

Usage: pixi run fetch-flood-zones   (slow; caches each county, so it can resume; needs fetch-counties)
"""
import json
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
CACHE = Path("data/raw/place/fema")
REGIONS = Path("data/raw/geo/regions_study.parquet")
OUT = Path("data/raw/place/flood_zones.csv")
CRS = 5070
PAGE = 500
MIN_SHARE = 0.001


def page(bounds, offset, tries=5):
    """One page of flood zones, or None after `tries` failures."""
    params = {"where": "SFHA_TF='T'", "geometry": ",".join(map(str, bounds)), "geometryType": "esriGeometryEnvelope",
              "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "FLD_ZONE",
              "returnGeometry": "true", "maxAllowableOffset": 0.0005, "resultOffset": offset,
              "resultRecordCount": PAGE, "orderByFields": "OBJECTID", "f": "geojson"}
    for attempt in range(tries):
        try:
            r = requests.get(URL, params=params, timeout=300)
            if r.ok and r.text.lstrip().startswith("{") and "features" in r.json():
                return r.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(20 * (attempt + 1))
    return None


def box_features(bounds, depth=0):
    """Every flood zone touching a box. A box the server can't page through (the deep pages of a big western
    county, e.g. Maricopa, AZ, fail at ~7,500 zones) is split into four and each fetched alike, up to depth 4.
    Zones crossing a split come back twice; the union in main() counts their area once."""
    features, offset = [], 0
    while True:
        got = page(bounds, offset, tries=3 if depth < 4 else 5)
        if got is None:
            if depth >= 4:
                raise RuntimeError(f"FEMA query failed for {bounds} at offset {offset}, even in pieces")
            minx, miny, maxx, maxy = bounds
            midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
            print(f"  splitting {tuple(round(b, 3) for b in bounds)} (failed at offset {offset})", flush=True)
            return [f for b in [(minx, miny, midx, midy), (midx, miny, maxx, midy),
                                (minx, midy, midx, maxy), (midx, midy, maxx, maxy)]
                    for f in box_features(b, depth + 1)]
        features += got["features"]
        if len(got["features"]) < PAGE:
            return features
        offset += PAGE


def zones(fips, bounds):
    path = CACHE / f"{fips}.geojson"
    if not path.exists():
        features = box_features(bounds)
        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    if not json.loads(path.read_text())["features"]:
        return None
    return gpd.read_file(path).set_crs(4326, allow_override=True).to_crs(CRS)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    regions = gpd.read_parquet(REGIONS)
    rows = []
    for i, r in enumerate(regions.itertuples(), 1):
        z = zones(r.region_fips, r.geometry.bounds)
        shape = gpd.GeoSeries([r.geometry], crs=4326).to_crs(CRS).iloc[0]
        share = None
        if z is not None:
            share = z.geometry.buffer(0).union_all().intersection(shape).area / shape.area
            share = share if share >= MIN_SHARE else None      # only slivers of a neighbour's zones along the border
        rows.append({"region_fips": r.region_fips, "flood_zone_share": share})
        print(f"{i}/{len(regions)} {r.region_fips} {share}", flush=True)
    out = pd.DataFrame(rows).round(4)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions, {out.flood_zone_share.notna().sum()} with flood zones")


if __name__ == "__main__":
    main()
