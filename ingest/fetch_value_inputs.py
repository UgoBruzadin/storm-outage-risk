"""State and county inputs for the value estimate (ml/value_states.py): crews, wages, prices, incomes, bills.

Sources, all public:
  BLS OEWS (May 2025, public API v1, no key)  power-line installers and repairers (SOC 49-9051) per state: how many
                                              (the crew pool) and their mean annual wage (the crew's cost)
  BEA Regional Price Parities (2024)          all-items price level per state, US = 100 (lodging, meals, trucks)
  Census ACS 5-year (2024), B19013            median household income per state and county (an input of the ICE
                                              residential cost model)
  EIA-861 (2024), Sales_Ult_Cust              customers, MWh and revenue by sector (residential, commercial,
                                              industrial) per state: retail prices, the average bill, MWh per
                                              business customer, and what customers pay the utilities in total

EIA-861 counting follows EIA's state tables: customers from bundled and delivery-only rows (an energy-only customer
has no lines of its own); MWh from bundled and energy-only rows (a delivery row re-counts energy someone else sold);
revenue from every row (delivery charges and energy charges are both part of the bill).

Outputs:
  data/raw/place/value_state.csv    one row per study state
  data/raw/place/value_county.csv   county_fips, median_hh_income

Usage: pixi run python -m ingest.fetch_value_inputs   (resumable: downloads are kept in data/raw/place/value/)
"""
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests

DIR = Path("data/raw/place/value")
OUT_STATE, OUT_COUNTY = Path("data/raw/place/value_state.csv"), Path("data/raw/place/value_county.csv")
SEED = pd.read_csv("dbt/seeds/study_states.csv", dtype=str)
UA = {"User-Agent": "storm-outage-risk research client"}

BLS_API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_YEAR = "2025"                         # OEWS May 2025, the newest annual release the API serves
LINE_WORKERS = "499051"                   # SOC 49-9051 Electrical power-line installers and repairers
BEA_RPP = "https://apps.bea.gov/regional/zip/SARPP.zip"
RPP_YEAR = "2024"
ACS_YEAR = 2024
ACS = (f"https://www2.census.gov/programs-surveys/acs/summary_file/{ACS_YEAR}/table-based-SF/data/5YRData/"
       f"acsdt5y{ACS_YEAR}-b19013.dat")
EIA_YEAR = 2024
EIA = f"https://www.eia.gov/electricity/data/eia861/zip/f861{EIA_YEAR}.zip"
SECTORS = {"RESIDENTIAL": "res", "COMMERCIAL": "com", "INDUSTRIAL": "ind"}


def cached(name, url):
    path = DIR / name
    if not path.exists():
        DIR.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, headers=UA, timeout=300)
        r.raise_for_status()
        if r.headers.get("Content-Type", "").startswith("text/html"):     # an error page served with 200
            raise RuntimeError(f"{url} returned a web page, not data")
        path.write_bytes(r.content)
    return path


def line_workers():
    """Employment (datatype 01) and mean annual wage (04) of line workers, per state."""
    series = {f"OEUS{fips}00000000000{LINE_WORKERS}{dt}": (fips, col)
              for fips in SEED.state_fips for dt, col in (("01", "line_workers"), ("04", "line_wage_mean"))}
    ids, rows = list(series), {}
    for i in range(0, len(ids), 25):                                  # v1 takes 25 series per request
        body = json.dumps({"seriesid": ids[i:i + 25], "startyear": BLS_YEAR, "endyear": BLS_YEAR})
        path = DIR / f"bls_oews_{BLS_YEAR}_{i // 25}.json"
        if not path.exists():
            DIR.mkdir(parents=True, exist_ok=True)
            r = requests.post(BLS_API, data=body, headers={**UA, "Content-Type": "application/json"}, timeout=120)
            r.raise_for_status()
            if r.json().get("status") != "REQUEST_SUCCEEDED":
                raise RuntimeError(r.json().get("message"))
            path.write_bytes(r.content)
        for s in json.loads(path.read_text())["Results"]["series"]:
            fips, col = series[s["seriesID"]]
            point = next((d for d in s["data"] if d["year"] == BLS_YEAR), None)
            # "-" or a footnote code means suppressed: left blank, and ml/value_states.py says which
            value = pd.to_numeric(point["value"].replace(",", ""), errors="coerce") if point else float("nan")
            rows.setdefault(fips, {})[col] = value
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("state_fips")


def price_parity():
    z = zipfile.ZipFile(cached("SARPP.zip", BEA_RPP))
    name = next(n for n in z.namelist() if n.startswith("SARPP_STATE") and n.endswith(".csv"))
    d = pd.read_csv(io.BytesIO(z.read(name)), dtype=str, encoding="latin1")
    d = d[d.LineCode.str.strip() == "1"]                               # RPPs: all items
    d["state_fips"] = d.GeoFIPS.str.strip().str.strip('"').str[:2]
    return pd.to_numeric(d.set_index("state_fips")[RPP_YEAR], errors="coerce").rename("rpp")


def income(level):
    """Median household income (B19013) per state or county, from the ACS summary file (no API key needed)."""
    d = pd.read_csv(cached(f"acsdt5y{ACS_YEAR}-b19013.dat", ACS), sep="|", dtype=str)
    prefix = {"state": "0400000US", "county": "0500000US"}[level]
    d = d[d.GEO_ID.str.startswith(prefix)]
    value = pd.to_numeric(d.B19013_E001, errors="coerce").where(lambda v: v > 0)   # negative = not available
    return pd.Series(value.to_numpy(), index=d.GEO_ID.str[len(prefix):].to_numpy(), name="median_hh_income")


def eia_sales():
    z = zipfile.ZipFile(cached(f"f861{EIA_YEAR}.zip", EIA))
    name = next(n for n in z.namelist() if n.startswith(f"Sales_Ult_Cust_{EIA_YEAR}"))
    d = pd.read_excel(io.BytesIO(z.read(name)), header=[0, 1, 2])
    flat = [" ".join(str(x) for x in c if "Unnamed" not in str(x)).strip() for c in d.columns]
    d.columns = flat
    state = next(c for c in flat if c.endswith(" State") or c == "State")
    service = next(c for c in flat if c.endswith("Service Type"))
    d = d[d[state].isin(SEED.state_abbr)]
    lines, energy = d[service].isin(["Bundled", "Delivery"]), d[service].isin(["Bundled", "Energy"])
    out = {}
    for sector, short in SECTORS.items():
        col = {kind: next(c for c in flat if c.startswith(f"{sector} {kind}"))
               for kind in ("Revenues", "Sales", "Customers")}
        num = {k: pd.to_numeric(d[c], errors="coerce").fillna(0) for k, c in col.items()}
        out[f"cust_{short}"] = num["Customers"][lines].groupby(d[state]).sum()
        out[f"mwh_{short}"] = num["Sales"][energy].groupby(d[state]).sum()
        out[f"rev_{short}"] = 1000 * num["Revenues"].groupby(d[state]).sum()          # thousand dollars -> $
    t = pd.DataFrame(out)
    for short in SECTORS.values():
        t[f"price_{short}"] = t[f"rev_{short}"] / (1000 * t[f"mwh_{short}"])            # $ per kWh
        t[f"mwh_per_{short}"] = t[f"mwh_{short}"] / t[f"cust_{short}"]
    t["bill_res_month"] = t.rev_res / t.cust_res / 12
    t["utility_revenue"] = t[[f"rev_{s}" for s in SECTORS.values()]].sum(axis=1)
    return t.rename_axis("state_abbr")


def main():
    states = SEED.set_index("state_fips")[["state_abbr", "state_name"]]
    t = states.join(line_workers()).join(price_parity()).join(income("state"))
    t = t.reset_index().merge(eia_sales().reset_index(), on="state_abbr", how="left")
    OUT_STATE.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT_STATE, index=False, float_format="%.6g")
    c = income("county").rename_axis("county_fips").reset_index()
    c[c.county_fips.str[:2].isin(SEED.state_fips)].to_csv(OUT_COUNTY, index=False)
    missing = t.columns[t.isna().any()].tolist()
    print(f"{len(t)} states -> {OUT_STATE}; {len(c)} counties -> {OUT_COUNTY}")
    if missing:
        print("blank (suppressed or not reported):", {m: t.loc[t[m].isna(), "state_abbr"].tolist() for m in missing})


if __name__ == "__main__":
    main()
