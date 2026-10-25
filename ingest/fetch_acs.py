"""Census ACS 5-year tables for housing age and density (all U.S. geographies).

The Census API now requires a key, so this uses the key-free "table-based
summary files" instead: one pipe-delimited file per table, every geography.
dbt filters them to MO + IL counties (GEO_ID '0500000US<fips>').

  B25034  year structure built (counts by decade)   -> share of homes built before 1960
  B25035  median year structure built
  B01003  total population
  B25001  housing units

Why housing age? Older neighborhoods tend to have mature trees *and* older
overhead lines — a proxy for both, since neither is measured directly.

Output: data/raw/acs/acsdt5y<year>-<table>.dat
Usage:  pixi run fetch-acs
"""
from pathlib import Path

import requests

YEAR = 2024
TABLES = ["b25034", "b25035", "b01003", "b25001"]
BASE = f"https://www2.census.gov/programs-surveys/acs/summary_file/{YEAR}/table-based-SF/data/5YRData"
OUT_DIR = Path("data/raw/acs")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        out = OUT_DIR / f"acsdt5y{YEAR}-{table}.dat"
        if out.exists():              # idempotent: skip files we already have
            continue
        with requests.get(f"{BASE}/{out.name}", stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(out, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        print("saved", out)


if __name__ == "__main__":
    main()
