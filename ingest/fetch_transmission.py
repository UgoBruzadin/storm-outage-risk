"""High-voltage power lines per region (HIFLD Electric Power Transmission Lines).

Transmission only: local distribution lines, which storms usually bring down, aren't public, and HIFLD's substation
layer is no longer open. The layer describes the grid around 2023.

Output: data/raw/place/transmission.csv
  transmission_km_per_km2    length of transmission lines per km2 of land
  transmission_hv_km_per_km2 the same for lines of 230 kV and up

Usage: pixi run fetch-transmission   (needs fetch-counties)
"""
import json
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

URL = ("https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
       "Electric_Power_Transmission_Lines/FeatureServer/0/query")
RAW = Path("data/raw/place/hifld/transmission_study.geojson")   # lines inside the study area's bounding box
REGIONS = Path("data/raw/geo/regions_study.parquet")
OUT = Path("data/raw/place/transmission.csv")
CRS = 5070
PAGE = 500                                   # ids per request
HIGH_KV = 230


def query(params, post=False):
    """One query, retried with a growing pause; the parsed JSON."""
    for attempt in range(8):
        try:
            r = (requests.post(URL, data=params, timeout=300) if post
                 else requests.get(URL, params=params, timeout=300))
            body = r.json() if r.ok else {}
        except (requests.RequestException, ValueError):
            body = {}
        if "error" not in body and body:
            return body
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"HIFLD query failed: {params.get('where') or 'by id'}")


def lines(bounds):
    """Every line in the layer: its ids, then the lines a chunk of ids at a time. Paging the whole layer by offset
    or in OBJECTID order fails on this server (the envelope query and the sorted pages time out), and the
    per-region clip in main() drops lines outside the study area anyway."""
    if not RAW.exists():
        ids = sorted(query({"where": "1=1", "returnIdsOnly": "true", "f": "json"})["objectIds"])
        features = []
        for i in range(0, len(ids), PAGE):
            features += query({"objectIds": ",".join(map(str, ids[i:i + PAGE])), "outSR": 4326,
                               "outFields": "OBJECTID,VOLTAGE", "f": "geojson"}, post=True)["features"]
        print(f"{len(features)} of {len(ids)} lines fetched", flush=True)
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return gpd.read_file(RAW).set_crs(4326, allow_override=True).to_crs(CRS)


def main():
    regions = gpd.read_parquet(REGIONS)
    grid = lines(regions.total_bounds)
    print(f"{len(grid)} line segments; voltage known for {(grid.VOLTAGE > 0).mean():.0%}", flush=True)
    regions = regions.to_crs(CRS)
    rows = []
    for r in regions.itertuples():
        inside = grid.clip(r.geometry)
        km2 = r.land_m2 / 1e6
        rows.append({"region_fips": r.region_fips, "transmission_km_per_km2": inside.length.sum() / 1000 / km2,
                     "transmission_hv_km_per_km2": inside[inside.VOLTAGE >= HIGH_KV].length.sum() / 1000 / km2})
    out = pd.DataFrame(rows).round(5)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions")


if __name__ == "__main__":
    main()
