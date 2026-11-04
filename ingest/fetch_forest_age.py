"""Stand age per region, from the Forest Inventory's own field plots (USFS FIA DataMart).

Stand age isn't in TreeMap, but FIA's condition table has it for each forested part of each plot. This averages it per
county, weighted by the share of the plot in that condition. Only surveys from 2014-2019 are used: one full survey
cycle, all before the training years. Counties with little forest have few plots, so their averages are noisy; a county
with fewer than 5 plots is left blank.

Output: data/raw/place/forest_age.csv
  stand_age_mean     average stand age, years
  stand_age_old      share of forest in stands 80 years or older
  stand_age_plots    number of forested plots behind the numbers (a check, not an input)

Usage: pixi run fetch-forest-age   (needs fetch-counties)
"""
from pathlib import Path

import pandas as pd
import requests

URL = "https://apps.fs.usda.gov/fia/datamart/CSV/{state}_COND.csv"
STATES = {"MO": "29", "IL": "17"}
DIR = Path("data/raw/place/fia")
REGIONS = Path("data/raw/geo/regions_study.csv")
OUT = Path("data/raw/place/forest_age.csv")
COLUMNS = ["PLT_CN", "INVYR", "COUNTYCD", "COND_STATUS_CD", "STDAGE", "CONDPROP_UNADJ"]
MIN_PLOTS = 5


def region_of(fips):
    return "29189+29510" if fips in {"29189", "29510"} else fips


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    parts = []
    for state, code in STATES.items():
        path = DIR / f"{state}_COND.csv"
        if not path.exists():
            r = requests.get(URL.format(state=state), timeout=600)
            r.raise_for_status()
            path.write_bytes(r.content)
        d = pd.read_csv(path, usecols=COLUMNS)
        parts.append(d.assign(fips=code + d.COUNTYCD.astype(int).astype(str).str.zfill(3)))
    c = pd.concat(parts)
    c = c[c.COND_STATUS_CD.eq(1) & c.INVYR.between(2014, 2019) & c.STDAGE.ge(0)].copy()
    c["region_fips"] = c.fips.map(region_of)
    c["old"] = c.STDAGE >= 80
    rows = []
    for fips, g in c.groupby("region_fips"):
        w = g.CONDPROP_UNADJ
        rows.append({"region_fips": fips, "stand_age_mean": (g.STDAGE * w).sum() / w.sum(),
                     "stand_age_old": (g.old * w).sum() / w.sum(), "stand_age_plots": g.PLT_CN.nunique()})
    out = pd.DataFrame(rows)
    out.loc[out.stand_age_plots < MIN_PLOTS, ["stand_age_mean", "stand_age_old"]] = None
    regions = pd.read_csv(REGIONS, dtype=str)[["region_fips"]]
    out = regions.merge(out, how="left").fillna({"stand_age_plots": 0}).round(4)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions, {out.stand_age_mean.notna().sum()} with an age")


if __name__ == "__main__":
    main()
