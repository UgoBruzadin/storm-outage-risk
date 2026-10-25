"""NOAA Storm Events database: severe weather reports, 2014–2025, all states.

Each row is one reported event (thunderstorm wind, tornado, hail, ice storm,
flash flood...) with a begin/end time, the county (or forecast zone) it hit,
and often a measured/estimated magnitude (wind in knots, hail in inches).
Used to say "a storm hit this county in this 6-hour block" — independently
of the model's weather inputs.

NCEI re-publishes files when they're revised, so the file name carries a
creation date (..._d2024_c20260728.csv.gz). We list the directory and take
the newest file per year. dbt filters to MO + IL.

Winter events (ice storm, winter storm, high wind...) are reported by NWS
forecast *zone* (CZ_TYPE = 'Z'), not county. The NWS zone–county correlation
file maps zones to county FIPS; we download its newest version too.

Output: data/raw/storm_events/StormEvents_details-ftp_v1.0_d<year>_c<date>.csv.gz
        data/raw/storm_events/zone_county_<bpDDmmYY>.dbx
Usage:  pixi run fetch-storm-events
"""
import re
from pathlib import Path

import requests

BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
ZONE_PAGE = "https://www.weather.gov/gis/ZoneCounty"
YEARS = range(2014, 2026)
OUT_DIR = Path("data/raw/storm_events")


def fetch_zone_county():
    page = requests.get(ZONE_PAGE, timeout=60).text
    links = re.findall(r'href="(/source/gis/Shapefiles/County/(bp\d{2}[a-z]{2}\d{2})\.dbx)"', page)
    # file names carry the date as DDmonYY, e.g. bp16ap26 = 16 Apr 2026: pick the newest
    months = ["ja", "fe", "mr", "ap", "my", "jn", "jl", "au", "se", "oc", "no", "de"]
    newest = max(links, key=lambda l: (l[1][6:8], months.index(l[1][4:6]), l[1][2:4]))
    out = OUT_DIR / f"zone_county_{newest[1]}.dbx"
    if not out.exists():
        r = requests.get("https://www.weather.gov" + newest[0], timeout=60)
        r.raise_for_status()
        out.write_bytes(r.content)
        print("saved", out)


def main():
    fetch_zone_county()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    listing = requests.get(BASE, timeout=60).text
    for year in YEARS:
        names = sorted(set(re.findall(rf"StormEvents_details-ftp_v1\.0_d{year}_c\d{{8}}\.csv\.gz", listing)))
        if not names:
            print(f"{year}: no file found")
            continue
        name = names[-1]                       # newest revision
        out = OUT_DIR / name
        stale = [p for p in OUT_DIR.glob(f"StormEvents_details-ftp_v1.0_d{year}_c*.csv.gz") if p.name != name]
        for p in stale:                        # keep one file per year
            p.unlink()
        if out.exists():
            continue
        r = requests.get(BASE + name, timeout=300)
        r.raise_for_status()
        out.write_bytes(r.content)
        print("saved", out)


if __name__ == "__main__":
    main()
