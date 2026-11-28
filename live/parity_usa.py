"""Do the USA live inputs match the ones the model was tested on? live.usa run end to end on past hours, against the
2025 test rows (usa_final_test.scored_states: the warehouse table, each run's window inputs, usa_ablation.add_inputs).

The live side reads only what the live job reads: HRRR from the AWS archive (past hours too), NWS warnings and SPC
outlooks from IEM, static_usa/. The test side reads the warehouse, whose past weather came from Open-Meteo, so small
differences in the weather inputs are expected (Open-Meteo rounds); anything else is a bug.

Usage: pixi run python -m live.parity_usa [--hours 2025-05-16T21 ...]
Writes ml/results/live_usa_parity.csv: per input, the share of county-hours that agree and the largest difference.
"""
import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from live import usa
from ml import data
from ml import forecast_test as ft
from ml import usa_ablation as ua
from ml.moving_window import THRESHOLD_PCT

HOURS = ["2025-05-16T21", "2025-02-16T12", "2025-03-14T15", "2025-03-04T23", "2025-07-04T03", "2025-12-01T06"]
OUT = data.ROOT / "ml" / "results" / "live_usa_parity.csv"


def expected(hour, ages):
    """The test rows of every county at `hour` (as usa_final_test.scored_states, for one hour)."""
    parts = []
    for s in data.warehouse_states():                # cached a state at a time by the 2025 test
        r = data.load_hourly(THRESHOLD_PCT, [hour.year], ua.LEAD, states=[s], float32=True)
        parts.append(r[r.block_start == hour])
    rows = pd.concat(parts, ignore_index=True)       # counties already out at `hour` aren't decisions: left out
    rows["region_fips"] = rows.region_fips.astype(str)
    f = ft.forecasts(f"{(hour - pd.Timedelta(days=1)):%Y-%m-%d}", f"{hour:%Y-%m-%d}")
    out = []
    for age in ages:
        w = ft.window_from_forecast(f, age).drop(columns=ua.DURATION)
        w = w.merge(ua.duration_forecast(f, age), on=["region_fips", "block_start"])
        out.append(w[w.block_start == hour].rename(columns={c: f"{c}|{age}" for c in ft.WINDOW}).drop(
            columns="block_start"))
    for w in out:
        rows = rows.merge(w, on="region_fips", how="left")
    rows["win_gust_max_ms"] = rows[f"win_gust_max_ms|{ages[0]}"]
    return ua.add_inputs(rows)


def compare(live, test, columns):
    m = live.merge(test, on="region_fips", suffixes=("_live", "_test"))
    rows = []
    for c in columns:
        a = pd.to_numeric(m[f"{c}_live"], errors="coerce").to_numpy(float)
        b = pd.to_numeric(m[f"{c}_test"], errors="coerce").to_numpy(float)
        both = ~np.isnan(a) & ~np.isnan(b)
        close = np.isclose(a, b, rtol=0.01, atol=0.05) | (np.isnan(a) & np.isnan(b))
        rows.append({"input": c, "agree": close.mean(), "both_known": both.mean(),
                     "live_only_unknown": (np.isnan(a) & ~np.isnan(b)).mean(),
                     "test_only_unknown": (~np.isnan(a) & np.isnan(b)).mean(),
                     "max_abs_diff": float(np.nanmax(np.abs(a - b))) if both.any() else np.nan,
                     "corr": float(np.corrcoef(a[both], b[both])[0, 1]) if both.sum() > 2 and np.std(b[both]) > 0
                     else np.nan})
    return pd.DataFrame(rows), len(m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", nargs="*", default=HOURS)
    a = ap.parse_args()
    meta = json.loads((usa.MODEL / "meta.json").read_text())
    window = [c for c in meta["features"] if c.startswith("win_")]
    base = [c for c in meta["features"] if c not in window]
    columns = base + [f"{c}|{age}" for age in meta["run_ages"] for c in window]
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "store.parquet"        # one store across the hours, as the live job keeps one
        for h in a.hours:
            hour = pd.Timestamp(h)
            _, live = usa.run(hour, Path(tmp), store)
            test = expected(hour, meta["run_ages"])
            r, n = compare(live, test, columns)
            print(f"{hour}: {n} counties, {(r.agree > 0.99).sum()} of {len(r)} inputs agree on 99%+", flush=True)
            parts.append(r.assign(hour=hour, counties=n))
            store.unlink()                         # the hours are days apart: start each from the archive
    df = pd.concat(parts)
    s = df.groupby("input", sort=False).agg(agree=("agree", "mean"), worst_hour=("agree", "min"),
                                            live_only_unknown=("live_only_unknown", "mean"),
                                            test_only_unknown=("test_only_unknown", "mean"),
                                            max_abs_diff=("max_abs_diff", "max"), corr=("corr", "min"))
    s.to_csv(OUT)
    print(s.sort_values("agree").head(30).to_string(float_format=lambda v: f"{v:.4g}"))
    print(f"{(s.agree > 0.99).sum()} of {len(s)} inputs agree on 99%+ of county-hours; wrote {OUT}")


if __name__ == "__main__":
    main()
