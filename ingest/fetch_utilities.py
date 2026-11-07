"""Which utilities serve each region, and their past reliability (EIA Form 861, 2015-2019).

The service territory file lists the counties where each utility has distribution equipment. It doesn't say how many
customers a utility has in each county, so a utility's customers in the state are split evenly over its counties there:
a rough weight, used for the shares below. Retail power marketers sell power without running lines, so they're left out.
Only years before the training period are used, so reliability can't reflect the storms being predicted.

Output: data/raw/place/utilities.csv
  util_count                     utilities with equipment in the region
  util_share_iou, util_share_coop, util_share_public
                                 rough share of customers with investor-owned, co-op and public utilities
  util_saidi, util_saifi         outage minutes and interruptions per customer, excl. major event days (mean 2015-19)
  util_saidi_med                 outage minutes per customer, including major event days (mean 2015-19)

Usage: pixi run fetch-utilities   (needs fetch-counties)
"""
import io
import re
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

URL = "https://www.eia.gov/electricity/data/eia861/archive/zip/f861{year}.zip"
DIR = Path("data/raw/place/eia")
COUNTIES = Path("data/raw/geo/cb_2023_us_county_500k.zip")
REGIONS = Path("data/raw/geo/regions_study.csv")
OUT = Path("data/raw/place/utilities.csv")
YEARS, LATEST = range(2015, 2020), 2019
SEED = pd.read_csv("dbt/seeds/study_states.csv", dtype=str)                   # the study area
STATES = dict(zip(SEED.state_abbr, SEED.state_fips, strict=True))
GROUPS = {"Investor Owned": "iou", "Cooperative": "coop", "Municipal": "public", "Political Subdivision": "public",
          "State": "public", "Federal": "public"}


def archive(year):
    path = DIR / f"f861{year}.zip"
    if not path.exists():
        r = requests.get(URL.format(year=year), timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return zipfile.ZipFile(path)


def sheet(year, prefix, header, sheet_name=0):
    z = archive(year)
    name = next(n for n in z.namelist() if n.startswith(f"{prefix}_{year}"))
    return pd.read_excel(io.BytesIO(z.read(name)), header=header, sheet_name=sheet_name)


def county_key(name):
    return re.sub(r"[^a-z]", "", str(name).lower().replace("saint ", "st ").replace("sainte ", "ste "))


def customers():
    """Customers per utility and state: bundled and delivery rows, as energy-only customers have no lines."""
    d = sheet(LATEST, "Sales_Ult_Cust", [0, 1, 2])
    flat = [" ".join(str(x) for x in c if "Unnamed" not in str(x)).strip() for c in d.columns]
    d.columns = flat
    number = next(c for c in flat if c.endswith("Utility Number"))
    state = next(c for c in flat if c.endswith(" State") or c == "State")
    service = next(c for c in flat if c.endswith("Service Type"))
    total = next(c for c in flat if c.startswith("TOTAL") and c.endswith("Count"))
    d = d[d[state].isin(STATES) & d[service].isin(["Bundled", "Delivery"])]
    d = d.assign(n=pd.to_numeric(d[total], errors="coerce"))
    return d.groupby([number, state]).n.sum().rename_axis(["utility", "state"])


def reliability():
    parts = []
    for year in YEARS:
        d = sheet(year, "Reliability", 1)
        d = d[d["State"].isin(STATES)]
        parts.append(pd.DataFrame({
            "utility": d["Utility Number"], "state": d["State"],
            "saidi_med": pd.to_numeric(d["SAIDI With MED"], errors="coerce"),
            "saidi": pd.to_numeric(d["SAIDI Without MED"], errors="coerce"),
            "saifi": pd.to_numeric(d["SAIFI Without MED"], errors="coerce")}))
    return pd.concat(parts).groupby(["utility", "state"]).mean()


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    territory = sheet(LATEST, "Service_Territory", 0)
    territory = territory[territory.State.isin(STATES)]
    # each utility is listed once, under its home state, so look it up by number alone
    owners = sheet(LATEST, "Utility_Data", 1).drop_duplicates("Utility Number")
    owners = owners.set_index("Utility Number")["Ownership Type"]
    names = gpd.read_file(f"zip://{COUNTIES}", ignore_geometry=True)
    names = names[names.STATEFP.isin(STATES.values())]
    lookup = {(s, county_key(n)): g for s, code in STATES.items()
              for n, g in names[names.STATEFP == code][["NAME", "GEOID"]].values}

    t = pd.DataFrame({"utility": territory["Utility Number"], "state": territory.State, "county": territory.County})
    t["fips"] = [lookup.get((s, county_key(c))) for s, c in zip(t.state, t.county, strict=True)]
    missing = sorted(set(t[t.fips.isna()].county.astype(str) + ", " + t[t.fips.isna()].state))
    print(f"{t.fips.isna().sum()} territory rows not matched to a county: {missing}", flush=True)
    t = t.dropna(subset=["fips"])
    t["owner"] = t.utility.map(owners)
    t = t[t.owner.isin(GROUPS)].drop_duplicates()
    t["region_fips"] = t.fips.where(~t.fips.isin(["29189", "29510"]), "29189+29510")
    t["group"] = t.owner.map(GROUPS)
    served = t.groupby(["utility", "state"]).region_fips.nunique().rename("n_counties")
    t = t.join(customers().rename("cust"), on=["utility", "state"]).join(served, on=["utility", "state"])
    t["weight"] = t.cust.fillna(0) / t.n_counties
    t = t.join(reliability(), on=["utility", "state"])

    rows = []
    for fips, g in t.groupby("region_fips"):
        g = g.drop_duplicates(["utility", "state"])
        w = g.weight
        row = {"region_fips": fips, "util_count": g.utility.nunique()}
        for group in ("iou", "coop", "public"):
            row[f"util_share_{group}"] = w[g.group == group].sum() / w.sum() if w.sum() else np.nan
        for out_name, column in (("util_saidi", "saidi"), ("util_saifi", "saifi"), ("util_saidi_med", "saidi_med")):
            known = g[column].notna() & w.gt(0)
            row[out_name] = (g[column] * w)[known].sum() / w[known].sum() if known.any() else np.nan
        rows.append(row)
    out = pd.read_csv(REGIONS, dtype=str)[["region_fips"]].merge(pd.DataFrame(rows), how="left").round(4)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions, {out.util_count.notna().sum()} with utilities, "
          f"{out.util_saidi.notna().sum()} with reliability")


if __name__ == "__main__":
    main()
