"""County shapes for the study states, as analysis regions.

Downloads the Census cartographic boundary file (1:500k, small and clean),
keeps the states listed in dbt/seeds/study_states.csv (the single source of
truth for the study area), and merges St. Louis City (29510) + County (29189)
into one region "29189+29510" — the same merge the outage data needs (see
docs/data-notes.md). Writes:

  data/raw/geo/regions_study.parquet  GeoParquet, one row per region, EPSG:4326
  data/raw/geo/regions_study.csv      the same without geometry (+ a weather point)

The weather point is a `representative_point()`: guaranteed to be inside the
shape (a plain centroid can fall outside an oddly shaped county).

Usage: pixi run fetch-counties
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
OUT_DIR = Path("data/raw/geo")
STATES_CSV = Path("dbt/seeds/study_states.csv")
STL_PARTS = {"29189", "29510"}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    states = pd.read_csv(STATES_CSV, dtype=str).set_index("state_fips")["state_name"].to_dict()
    zip_path = OUT_DIR / Path(URL).name
    if not zip_path.exists():          # idempotent: skip files we already have
        r = requests.get(URL, timeout=120)
        r.raise_for_status()
        zip_path.write_bytes(r.content)

    shp = gpd.read_file(f"zip://{zip_path}")
    counties = shp[shp["STATEFP"].isin(states)].copy()
    counties["fips_code"] = counties["GEOID"]
    counties["region_fips"] = counties["fips_code"].where(~counties["fips_code"].isin(STL_PARTS), "29189+29510")
    counties["region"] = counties["NAME"].where(~counties["fips_code"].isin(STL_PARTS), "St. Louis City + County")
    counties["state"] = counties["STATEFP"].map(states)

    # One shape per region; land/water areas add up across merged counties
    regions = counties.dissolve(
        by="region_fips",
        aggfunc={"region": "first", "state": "first", "ALAND": "sum", "AWATER": "sum"},
    ).reset_index()
    regions = regions.rename(columns={"ALAND": "land_m2", "AWATER": "water_m2"}).to_crs("EPSG:4326")

    # Weather point: inside the shape, computed in an equal-area projection
    points = regions.to_crs("EPSG:5070").representative_point().to_crs("EPSG:4326")
    regions["lat"] = points.y.round(4)
    regions["lon"] = points.x.round(4)

    regions.to_parquet(OUT_DIR / "regions_study.parquet")
    regions.drop(columns="geometry").to_csv(OUT_DIR / "regions_study.csv", index=False)
    print(f"{len(counties)} counties -> {len(regions)} regions written to {OUT_DIR}")


if __name__ == "__main__":
    main()
