"""Soil per region (USDA NRCS SSURGO, through Soil Data Access).

Asks for every soil map unit's acres in each county and its summary soil properties, then averages by acres. Map units
with no soil (water, quarries) are left out. A blank water table or bedrock depth means none was found within about
2 m of the surface, so those count as 201 cm, as in SSURGO's own convention.

Output: data/raw/place/soil.csv
  soil_poor_drain_share   share of acres somewhat poorly to very poorly drained
  soil_group_d_share      share of acres in hydrologic group D (including dual groups): water runs off, soaks in slowly
  soil_flood_share        share of acres flooding occasionally, frequently or very frequently
  soil_water_table_cm     shallowest depth to water table in the year, cm
  soil_bedrock_cm         depth to bedrock, cm: shallow soil means shallow roots

Usage: pixi run fetch-soil   (needs fetch-counties)
"""
from pathlib import Path

import pandas as pd
import requests

URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
STATES = {"MO": "29", "IL": "17"}
REGIONS = Path("data/raw/geo/regions_study.csv")
OUT = Path("data/raw/place/soil.csv")
RAW = Path("data/raw/place/soil/map_units_{state}.csv")
QUERY = """
SELECT lao.areasymbol, mao.areaovacres, ma.drclassdcd, ma.hydgrpdcd, ma.flodfreqdcd, ma.wtdepannmin, ma.brockdepmin
FROM laoverlap lao
JOIN muaoverlap mao ON mao.lareaovkey = lao.lareaovkey
JOIN muaggatt ma ON ma.mukey = mao.mukey
WHERE lao.areatypename = 'County or Parish' AND lao.areasymbol LIKE '{state}%'
"""
POOR = {"Somewhat poorly drained", "Poorly drained", "Very poorly drained"}
FLOODS = {"Occasional", "Frequent", "Very frequent"}
NUMERIC = ["areaovacres", "wtdepannmin", "brockdepmin"]


def map_units(state):
    path = Path(str(RAW).format(state=state))
    if path.exists():
        return pd.read_csv(path)
    r = requests.post(URL, json={"format": "JSON+COLUMNNAME", "query": QUERY.format(state=state)}, timeout=600)
    r.raise_for_status()
    table = r.json()["Table"]
    d = pd.DataFrame(table[1:], columns=table[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(path, index=False)
    return pd.read_csv(path)


def main():
    parts = []
    for state, code in STATES.items():
        d = map_units(state)
        parts.append(d.assign(fips=code + d.areasymbol.str[2:]))
    d = pd.concat(parts)
    d[NUMERIC] = d[NUMERIC].apply(pd.to_numeric)
    d = d[d.drclassdcd.notna() & d.areaovacres.gt(0)].copy()
    d["region_fips"] = d.fips.where(~d.fips.isin(["29189", "29510"]), "29189+29510")
    rows = []
    for fips, g in d.groupby("region_fips"):
        a = g.areaovacres
        rows.append({
            "region_fips": fips,
            "soil_poor_drain_share": a[g.drclassdcd.isin(POOR)].sum() / a.sum(),
            "soil_group_d_share": a[g.hydgrpdcd.fillna("").str.contains("D")].sum() / a.sum(),
            "soil_flood_share": a[g.flodfreqdcd.isin(FLOODS)].sum() / a.sum(),
            "soil_water_table_cm": (g.wtdepannmin.fillna(201) * a).sum() / a.sum(),
            "soil_bedrock_cm": (g.brockdepmin.fillna(201) * a).sum() / a.sum(),
        })
    out = pd.read_csv(REGIONS, dtype=str)[["region_fips"]].merge(pd.DataFrame(rows), how="left").round(4)
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(out)} regions, {out.soil_poor_drain_share.notna().sum()} with soil")


if __name__ == "__main__":
    main()
