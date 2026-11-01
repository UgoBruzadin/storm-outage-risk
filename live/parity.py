"""Does the live code compute the same inputs as the training table? (run locally: needs the warehouse)

Feeds live/features.py the raw files the warehouse was built from (Open-Meteo HRRR CSVs, IEM warnings, the SPC
outlook shapefile) and compares every live model input, for a sample of 2025 decision hours, with
marts.mart_study__region_1h and ml.data.neighbor_features. The hours: the 2025 storm days with the most new outages,
plus random hours. The forecast window columns come from forecast_test.window_from_forecast in both, so they
aren't compared.

Usage: pixi run python -m live.parity
"""
import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd

from live import features as lf
from ml import data
from ml.forecast_test import WINDOW

RAW = data.ROOT / "data" / "raw"
TOL = 1e-6


def sample_hours(con, n_random=24, seed=0):
    storms = con.sql("""
        SELECT date_trunc('day', hour) AS day, count(*) AS n FROM marts.mart_study__region_1h
        WHERE year(hour) = 2025 AND pct_out >= 5 AND pct_out_now < 5 GROUP BY 1 ORDER BY n DESC LIMIT 4
    """).df().day
    storm_hours = [d + pd.Timedelta(hours=h) for d in storms for h in range(0, 24, 3)]
    rng = np.random.default_rng(seed)
    year = pd.date_range("2025-01-05", "2025-12-25", freq="h")
    return pd.DatetimeIndex(sorted(set(storm_hours) | set(year[rng.choice(len(year), n_random, replace=False)])))


def main():
    con = duckdb.connect(str(data.DB), read_only=True)
    hours = sample_hours(con)
    print(f"{len(hours)} decision hours", flush=True)

    files = sorted((RAW / "weather" / "hrrr").glob("*_2025.csv.gz"))
    raw = pd.concat([pd.read_csv(f, dtype={"region_fips": str}) for f in files], ignore_index=True)
    hw = lf.hourly_weather(raw)
    warn = pd.concat([pd.read_csv(RAW / "nws" / f"warnings_{y}.csv", dtype=str) for y in (2024, 2025)])
    regions = pd.read_parquet(lf.STATIC / "regions.parquet")
    outlooks = pd.concat([lf.outlook_table(gpd.read_file(RAW / "nws" / f"spc_day1_{y}.zip"), regions)
                          for y in (2024, 2025)], ignore_index=True)
    live = lf.model_rows(hw, warn, outlooks, hours)

    keys = ", ".join(f"TIMESTAMP '{h}'" for h in hours)
    mart = con.sql(f"SELECT * FROM marts.mart_study__region_1h WHERE hour IN ({keys})").df()
    con.close()
    mart = mart.rename(columns={"hour": "block_start", "hour_utc": "block_hour_utc"})
    nb = data.neighbor_features().rename(columns={"hour": "block_start"})
    mart = data.add_derived(mart.merge(nb, on=["region_fips", "block_start"], how="left"))

    cols = [c for c in lf.live_features() if c not in WINDOW]
    both = live.merge(mart, on=["region_fips", "block_start"], suffixes=("_live", "_mart"))
    print(f"rows: live {len(live):,}, training table {len(mart):,}, matched {len(both):,}")
    bad = {}
    for c in cols:
        a, b = both[f"{c}_live"].astype(float), both[f"{c}_mart"].astype(float)
        diff = ~(np.isclose(a, b, atol=TOL, rtol=TOL) | (a.isna() & b.isna()))
        if diff.any():
            bad[c] = int(diff.sum())
            ex = both.loc[diff, ["region_fips", "block_start", f"{c}_live", f"{c}_mart"]].head(3)
            print(f"MISMATCH {c}: {diff.sum()} rows\n{ex.to_string(index=False)}")
    # a match only means something if the sample has warnings, outlooks and storms in it
    nonzero = {c: int((both[f"{c}_mart"].astype(float) > 0).sum())
               for c in ("warn_svr", "warn_tor", "warn_winter", "spc_cat", "spc_wind_prob", "near_warn_share",
                         "hail_hours", "icing_hours")}
    print(f"rows with the input above zero: {nonzero}")
    has = both.has_weather_mart.astype(bool)
    print(f"{len(cols)} inputs compared on {len(both):,} rows ({has.sum():,} with full weather): "
          + ("all identical" if not bad else f"{len(bad)} differ: {bad}"))


if __name__ == "__main__":
    main()
