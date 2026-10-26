"""Official NWS / SPC forecasts for the study states, from the Iowa Environmental Mesonet archive.

These are what a utility has today without a model, so they are the baselines a
model has to beat (or add to):

  warnings   NWS warnings in force, by county or forecast zone: severe thunderstorm (SV),
             tornado (TO), high wind (HW), ice storm (IS), winter storm (WS), blizzard (BZ).
             Issued minutes to hours ahead of the hazard.
  outlooks   SPC Day 1 convective outlooks: categorical risk (TSTM, MRGL, SLGT, ENH,
             MDT, HIGH) and wind / tornado / hail probabilities, issued five times a day
             for the 12Z-12Z day. Issued hours ahead.

Warnings come one row per county/zone per warning update (NEW, CON, CAN, EXP).
Outlooks come as polygons; each is joined to the region's interior point here, so
dbt gets plain tables: one row per outlook product x region it covers.

Output: data/raw/nws/warnings_<year>.csv
        data/raw/nws/spc_day1_<year>.csv
Usage:  pixi run fetch-nws          (~1 min per year; skips years already saved)
"""
import io
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis"
YEARS = range(2014, 2026)
STATES = "MO,IL"
PHENOMENA = ["SV", "TO", "HW", "IS", "WS", "BZ"]
CATEGORICAL = {"TSTM": 1, "MRGL": 2, "SLGT": 3, "ENH": 4, "MDT": 5, "HIGH": 6}
REGIONS = Path("data/raw/geo/regions_study.parquet")
OUT_DIR = Path("data/raw/nws")


def get(url, params, tries=4):
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=300)
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(10 * 2 ** attempt)


def fetch_warnings(year):
    out = OUT_DIR / f"warnings_{year}.csv"
    if out.exists():
        return
    content = get(f"{IEM}/watchwarn.py", {
        "accept": "csv", "sts": f"{year}-01-01T00:00Z", "ets": f"{year + 1}-01-01T00:00Z",
        "location_group": "states", "states": STATES, "limitps": 1,
        "phenomena": ",".join(PHENOMENA), "significance": ",".join("W" * len(PHENOMENA)),
    })
    warnings = pd.read_csv(io.BytesIO(content), dtype=str)
    # county/zone rows only: storm-based polygons (gtype P) repeat the same warning
    warnings = warnings[warnings["gtype"] == "C"]
    cols = ["wfo", "phenomena", "significance", "eventid", "vtec_year", "status", "ugc",
            "utc_issue", "utc_expire", "product_id"]
    warnings[cols].to_csv(out, index=False)
    print("saved", out, len(warnings), "rows")


def fetch_outlooks(year, points):
    out = OUT_DIR / f"spc_day1_{year}.csv"
    raw = OUT_DIR / f"spc_day1_{year}.zip"                       # the shapefile as downloaded
    if out.exists():
        return
    if not raw.exists():
        raw.write_bytes(get(f"{IEM}/outlooks.py", {
            "d": 1, "type": "C", "sts": f"{year}-01-01T00:00Z", "ets": f"{year + 1}-01-01T00:00Z",
        }))
    polygons = gpd.read_file(raw).to_crs(points.crs)
    hits = gpd.sjoin(points, polygons, predicate="within")        # outlook polygons covering each region
    hits["level"] = hits["THRESHOLD"].map(CATEGORICAL)
    hits["prob"] = pd.to_numeric(hits["THRESHOLD"], errors="coerce")  # SIGN (hatched) -> NaN
    keys = ["PRODISS", "ISSUE", "EXPIRE", "CYCLE", "region_fips"]
    by_category = hits.pivot_table(index=keys, columns="CATEGORY", values=["level", "prob"], aggfunc="max")
    covered = pd.DataFrame({
        "spc_cat": by_category.get(("level", "CATEGORICAL")),
        "spc_wind_prob": by_category.get(("prob", "WIND")),
        "spc_tor_prob": by_category.get(("prob", "TORNADO")),
        "spc_hail_prob": by_category.get(("prob", "HAIL")),
    }, index=by_category.index)
    # Every product x every region, 0 where the outlook doesn't reach it. dbt picks the
    # latest product in force for each block, so a product that leaves a region out
    # must still be there to say "no risk here now".
    products = polygons[keys[:-1]].drop_duplicates()
    full = products.merge(points[["region_fips"]], how="cross").set_index(keys)
    table = full.join(covered).fillna(0).reset_index()
    table.columns = [c.lower() for c in table.columns]
    table.to_csv(out, index=False)
    print("saved", out, len(table), "rows")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    regions = gpd.read_parquet(REGIONS)
    # one point per region, guaranteed inside it (a centroid can fall outside an odd shape)
    points = gpd.GeoDataFrame(regions[["region_fips"]], geometry=regions.representative_point(), crs=regions.crs)
    for year in YEARS:
        fetch_warnings(year)
        fetch_outlooks(year, points)


if __name__ == "__main__":
    main()
