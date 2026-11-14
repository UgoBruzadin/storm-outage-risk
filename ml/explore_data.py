"""Tables for exploring where the 2025 model does well or badly (notebooks/explore_usa.ipynb).

  data/explore/decisions_2025.parquet  every scored 2025 decision (a region-hour, 2 hours ahead): did a new outage
                                       start, each model's chance, and what the model saw at decision time: the hour's
                                       weather, the weather of the window ahead (as it happened), warnings and
                                       outlook, recent outages, the place
  data/explore/counties_2025.parquet   one row per county: new outages, each model's PR-AUC and its ratio to
                                       warnings + outlook on the same rows, the share caught at the headline alert
                                       level, and the county's place data (warehouse + data/raw/place)

Built from the pipeline's saved 2025 predictions (forecast_test, forecast_ensemble) and the warehouse; nothing is
refitted. Rebuild after the pipeline reruns those steps.

Usage: pixi run python -m ml.explore_data
"""
import time

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap

from ml import data
from ml import forecast_test as ft
from ml.export_hourly import HEADLINE_SHARE, TEST_YEAR

CACHE = data.ROOT / "data" / "cache"
OUT = data.ROOT / "data" / "explore"
PLACE = data.ROOT / "data" / "raw" / "place"
DECISIONS = OUT / f"decisions_{TEST_YEAR}.parquet"
COUNTIES = OUT / f"counties_{TEST_YEAR}.parquet"

# short name: column in the saved predictions (export_hourly.MODELS, same models)
MODELS = {
    "p_official": "warnings + outlook",          # rate table of warnings + SPC outlook
    "p_no_forecast": "forecast-ready",           # weather now + place + recent outages + neighbours
    "p_newest": "p_newest",                      # + the newest HRRR run's window weather
    "p_mean": "p_mean",                          # + the mean over the five HRRR runs (headline)
    "p_perfect": "+ window weather: actual",     # + the window's weather as it happened (ceiling)
}
HOUR_COLS = ["customers", "gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms", "cape_max_jkg",
             "precip_sum_mm", "precip_max_1h_mm", "temp_min_c", "freezing_level_min_m", "icing_hours", "hail_hours",
             "precip_prev_72h_mm", "pct_out_now", "max_pct_out_prev_24h", "max_pct_out_prev_7d", "hours_since_outage",
             "warn_svr", "warn_tor", "warn_wind", "warn_winter", "spc_cat", "spc_wind_prob", "spc_tor_prob",
             "spc_hail_prob", "month", "day_of_week", "hour_utc"]
WINDOW_COLS = ["win_gust_max_ms", "win_wind10_max_ms", "win_cape_max_jkg", "win_precip_max_1h_mm",
               "win_precip_sum_mm", "win_temp_min_c", "win_icing_hours", "win_hail_hours"]


def decisions(con):
    """decisions_2025.parquet, joined in DuckDB (out of core)."""
    win = ft.actual_window(TEST_YEAR)[["region_fips", "block_start", *WINDOW_COLS]]
    win_path = OUT / "_window.parquet"
    win.to_parquet(win_path, index=False)
    del win
    p = ", ".join(f'a."{c}"::FLOAT AS {k}' if c in ("warnings + outlook", "forecast-ready", "+ window weather: actual")
                  else f"b.{c}::FLOAT AS {k}" for k, c in MODELS.items())
    hour = ", ".join(f"h.{c}" for c in HOUR_COLS)
    con.sql(f"""
        COPY (
          SELECT a.region_fips, h.state, h.region AS county, a.block_start,
                 (a.block_start - INTERVAL 12 HOUR)::DATE AS storm_day,   -- 12 UTC to 12 UTC (uncertainty.storm_day)
                 a.y::TINYINT AS y, {p}, b.p_low::FLOAT AS p_low, b.p_high::FLOAT AS p_high,
                 h.fut_max_pct_2::FLOAT AS outcome_peak_pct,              -- the outcome, never a model input
                 {hour}, {", ".join(f"w.{c}" for c in WINDOW_COLS)}
          FROM '{CACHE / f"forecast_test_{TEST_YEAR}_predictions.parquet"}' a
          JOIN '{CACHE / f"forecast_ensemble_{TEST_YEAR}.parquet"}' b USING (region_fips, block_start)
          LEFT JOIN marts.mart_study__region_1h h ON h.region_fips = a.region_fips AND h.hour = a.block_start
          LEFT JOIN '{win_path}' w ON w.region_fips = a.region_fips AND w.block_start = a.block_start
          ORDER BY a.region_fips, a.block_start
        ) TO '{DECISIONS}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 500000)""")
    win_path.unlink()


def county_scores(con):
    """Per county: each model's PR-AUC, its ratio to warnings + outlook, and the share of new outages caught at
    the headline alert level (the top HEADLINE_SHARE of all 2025 decisions, country-wide)."""
    d = con.sql(f"SELECT region_fips, y, {', '.join(MODELS)} FROM '{DECISIONS}'").df()
    level = {k: np.quantile(d[k].to_numpy(), 1 - HEADLINE_SHARE) for k in MODELS}
    rows = []
    for fips, g in d.groupby("region_fips", sort=False):
        y = g.y.to_numpy()
        row = {"region_fips": fips, "decisions": len(g), "new_outages": int(y.sum())}
        for k in MODELS:
            p = g[k].to_numpy()
            row[f"pr_auc_{k}"] = ap(y, p) if y.any() else np.nan
            row[f"caught_{k}"] = (p[y == 1] >= level[k]).mean() if y.any() else np.nan
            row[f"alert_hours_{k}"] = int((p >= level[k]).sum())
        rows.append(row)
    out = pd.DataFrame(rows)
    for k in MODELS:
        if k != "p_official":
            out[f"ratio_{k}"] = out[f"pr_auc_{k}"] / out["pr_auc_p_official"]
    out["base_rate"] = out.new_outages / out.decisions
    return out, level


def place(con):
    """The county's place data: the warehouse's resilience mart + every data/raw/place table."""
    df = con.sql("SELECT * FROM marts.mart_study__region_resilience").df()
    for f in sorted(PLACE.glob("*.csv")):
        df = df.merge(pd.read_csv(f, dtype={"region_fips": str}), on="region_fips", how="left")
    return df


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(data.DB), read_only=True)
    t = time.time()
    decisions(con)
    n, matched = con.sql(f"SELECT count(*), count(gust_max_ms) FROM '{DECISIONS}'").fetchall()[0]
    print(f"wrote {DECISIONS}: {n:,} decisions, hourly features for {matched / n:.2%} ({time.time() - t:.0f}s)",
          flush=True)
    scores, level = county_scores(con)
    counties = place(con).merge(scores, on="region_fips", how="right")
    counties.to_parquet(COUNTIES, index=False)
    print(f"wrote {COUNTIES}: {len(counties)} counties; alert levels (top {HEADLINE_SHARE:.2%} of decisions): "
          + ", ".join(f"{k} {v:.4f}" for k, v in level.items()), flush=True)


if __name__ == "__main__":
    main()
