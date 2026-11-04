"""High-voltage power lines per region (HIFLD Electric Power Transmission Lines).

Transmission only: local distribution lines, which storms usually bring down, aren't public, and HIFLD's substation
layer is no longer open. The layer describes the grid around 2023.

Output: data/raw/place/transmission.csv
  transmission_km_per_km2    length of transmission lines per km2 of land
  transmission_hv_km_per_km2 the same for lines of 230 kV and up

Usage: pixi run fetch-transmission   (needs fetch-counties)
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

URL = ("https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
       "Electric_Power_Transmission_Lines/FeatureServer/0/query")
RAW = Path("data/raw/place/hifld/transmission_mo_il.geojson")
REGIONS = Path("data/raw/geo/regions_study.parquet")
OUT = Path("data/raw/place/transmission.csv")
CRS = 5070
PAGE = 1000
HIGH_KV = 230


def lines(bounds):
    if not RAW.exists():
        features, offset = [], 0
        while True:
            r = requests.get(URL, params={
                "where": "1=1", "geometry": ",".join(map(str, bounds)), "geometryType": "esriGeometryEnvelope",
                "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "VOLTAGE",
                "resultOffset": offset, "resultRecordCount": PAGE, "f": "geojson"}, timeout=300)
            r.raise_for_status()
            got = r.json()["features"]
            features += got
            if len(got) < PAGE:
                break
            offset += PAGE
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
