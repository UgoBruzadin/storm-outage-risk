"""The live feeds, from the same places the training data came from (ingest/):

  weather      HRRR via Open-Meteo, the past hours (identical to the Historical Forecast API training used)
  warnings     NWS warnings, Iowa Environmental Mesonet (as ingest/fetch_nws.py)
  outlooks     SPC Day 1 convective outlooks, Iowa Environmental Mesonet (as ingest/fetch_nws.py)
  forecasts    HRRR runs as issued, hrrrzarr archive on AWS (as ingest/fetch_hrrr_forecast.py)
"""
import io
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

from ingest.fetch_hrrr_forecast import fetch_run
from ingest.fetch_nws import IEM, PHENOMENA, STATES
from ingest.fetch_weather import VARIABLES

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
AGENT = {"User-Agent": "storm-outage-risk live forecast (research, non-commercial)"}


def iso(t):
    return f"{t:%Y-%m-%dT%H:%M}Z"


def weather(regions, past_hours=12):
    """The past `past_hours` hours of HRRR per region (Open-Meteo, one request per 54 regions)."""
    parts = []
    for i in range(0, len(regions), 54):
        chunk = regions.iloc[i:i + 54]
        r = requests.get(OPEN_METEO, timeout=120, headers=AGENT, params={
            "latitude": ",".join(map(str, chunk.lat)), "longitude": ",".join(map(str, chunk.lon)),
            "hourly": ",".join(VARIABLES), "models": "ncep_hrrr_conus", "wind_speed_unit": "ms",
            "timezone": "GMT", "past_hours": past_hours, "forecast_hours": 1,
        })
        r.raise_for_status()
        replies = r.json() if isinstance(r.json(), list) else [r.json()]
        for fips, reply in zip(chunk.region_fips, replies, strict=True):
            parts.append(pd.DataFrame(reply["hourly"]).assign(region_fips=fips))
    return pd.concat(parts, ignore_index=True)


def warnings(start, end):
    """Warnings for the study states issued or in force between start and end, one row per county / zone."""
    r = requests.get(f"{IEM}/watchwarn.py", timeout=300, headers=AGENT, params={
        "accept": "csv", "sts": iso(start), "ets": iso(end), "location_group": "states", "states": STATES,
        "limitps": 1, "phenomena": ",".join(PHENOMENA), "significance": ",".join("W" * len(PHENOMENA)),
    })
    r.raise_for_status()
    w = pd.read_csv(io.BytesIO(r.content), dtype=str)
    return w[w.gtype == "C"] if len(w) else w


def outlooks(start, end):
    """SPC Day 1 categorical and probabilistic outlook polygons issued between start and end."""
    import geopandas as gpd
    r = requests.get(f"{IEM}/outlooks.py", timeout=300, headers=AGENT,
                     params={"d": 1, "type": "C", "sts": iso(start), "ets": iso(end)})
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".zip") as f:
        f.write(r.content)
        f.flush()
        return gpd.read_file(f.name)


def forecasts(regions, runs):
    """HRRR point forecasts (forecast hours 1-13) for each run in `runs`; runs not in the archive yet are missing."""
    points = tuple(regions[c].to_numpy() for c in ("region_fips", "tile_row", "tile_col", "row", "col"))
    with ThreadPoolExecutor(max_workers=16) as pool:
        found = [df for run in runs if (df := fetch_run(run, points, pool)) is not None]
    if not found:
        return None
    df = pd.concat(found, ignore_index=True)
    df["temp_c"] = df.pop("temp_k") - 273.15
    df["region_fips"] = df.region_fips.astype(str)
    return df.astype({c: np.float32 for c in df.columns if df[c].dtype == np.float64})
