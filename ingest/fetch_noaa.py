from pathlib import Path

import requests

# NOAA Global Hourly (ISD), mirrored on AWS Open Data since NCEI moved it
BASE = "https://noaa-global-hourly-pds.s3.amazonaws.com"
RAW_DIR = Path("data/raw/noaa")
STATIONS = {
    "72434013994": "KSTL",  # St. Louis Lambert International Airport
}


def download_year(station: str, year: int) -> Path:
    """Download one year of hourly observations for one station as CSV."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"noaa_{STATIONS[station]}_{year}.csv"
    if out.exists():          # idempotent: skip files we already have
        return out

    url = f"{BASE}/{year}/{station}.csv"
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return out


if __name__ == "__main__":
    for station in STATIONS:
        for year in range(2014, 2026):
            print("saved", download_year(station, year))
