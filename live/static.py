"""What the live job needs that doesn't change hour to hour, exported once from the warehouse into the repo.

  regions.parquet     place features (int_study__regions), the point Open-Meteo is asked about (as in
                      fetch_weather.py), the point SPC outlooks are read at (as in fetch_nws.py), and the HRRR grid
                      cell of fetch_hrrr_forecast.py
  neighbors.parquet   near and upwind pairs (int_study__region_neighbors)
  zones.parquet       NWS forecast zone -> county (stg_noaa__zone_county)

With --usa, the whole country into static_usa/, plus what the USA live model adds (live/model_usa):
  place.parquet       roads, location and the E47 place files per region (ml.data._static_tables)
  history.parquet     each region's outage history as of Jan 1 of the latest year in the warehouse

The GitHub Actions job has no warehouse, so these files are committed. Re-run after a dbt build changes them.

Usage: pixi run python -m live.static [--usa]
"""
import argparse
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd

from ingest.fetch_hrrr_forecast import grid_points
from ml import data

OUT = Path(__file__).parent / "static"
OUT_USA = Path(__file__).parent / "static_usa"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usa", action="store_true", help="the whole country, into static_usa/")
    usa = ap.parse_args().usa
    out = OUT_USA if usa else OUT
    out.mkdir(exist_ok=True)
    con = duckdb.connect(str(data.DB), read_only=True)
    places = con.sql("""
        SELECT region_fips, region, state, customers, land_km2, housing_per_km2, share_homes_pre1960,
               median_year_built, canopy_mean_pct, canopy_dense_share
        FROM intermediate.int_study__regions
    """).df()
    neighbors = con.sql("""
        SELECT region_fips, neighbor_fips, is_near, is_upwind FROM intermediate.int_study__region_neighbors
    """).df()
    zones = con.sql("SELECT zone_id, fips_code FROM staging.stg_noaa__zone_county").df()
    con.close()

    coords = pd.read_csv("data/raw/geo/regions_study.csv", dtype={"region_fips": str})[["region_fips", "lat", "lon"]]
    shapes = gpd.read_parquet("data/raw/geo/regions_study.parquet")[["region_fips", "geometry"]]
    inside = shapes.representative_point().to_crs("EPSG:4326")                 # as fetch_nws.py
    outlook = pd.DataFrame({"region_fips": shapes.region_fips, "outlook_lon": inside.x, "outlook_lat": inside.y})
    fips, trow, tcol, irow, icol = grid_points()
    grid = pd.DataFrame({"region_fips": fips, "tile_row": trow, "tile_col": tcol, "row": irow, "col": icol})

    regions = places.merge(coords, on="region_fips").merge(outlook, on="region_fips").merge(grid, on="region_fips")
    assert len(regions) == len(places) == (len(places) if usa else 216), len(regions)
    regions.sort_values("region_fips").to_parquet(out / "regions.parquet", index=False)
    neighbors.to_parquet(out / "neighbors.parquet", index=False)
    zones.to_parquet(out / "zones.parquet", index=False)
    print(f"wrote {len(regions)} regions, {len(neighbors)} neighbour pairs, {len(zones)} zone-county rows to {out}")
    if usa:
        county, hist = data._static_tables()
        county = county[county.region_fips.isin(regions.region_fips)]
        latest = int(hist.as_of_year.max())
        hist = hist[hist.as_of_year == latest].drop(columns="as_of_year")
        county.sort_values("region_fips").to_parquet(out / "place.parquet", index=False)
        hist.sort_values("region_fips").to_parquet(out / "history.parquet", index=False)
        missing = sorted(set(regions.region_fips) - set(county.region_fips))
        print(f"place inputs for {len(county)} regions (missing {missing[:5]}), history as of Jan 1 {latest}")


if __name__ == "__main__":
    main()
