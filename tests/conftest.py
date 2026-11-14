"""Shared test setup: a small synthetic test fixture of the app dataset, so tests never need the real data.

APP_DATA must point at it before app/lib.py is first imported (lib reads the
variable at import time), so it's set at module level here — pytest loads
conftest.py before any test module.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))          # views do `from lib import ...`
sys.path.insert(0, str(ROOT))                  # `from ml import ...`

APP_DATA = Path(tempfile.mkdtemp(prefix="app-data-"))
os.environ["APP_DATA"] = str(APP_DATA)

import ml.data  # noqa: E402  (after sys.path)

ml.data.TABLE_CACHE = Path(tempfile.mkdtemp(prefix="table-cache-"))    # tests never write into data/cache


def square(x, y):
    return json.dumps({"type": "Polygon", "coordinates": [[[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]]})


def write_fixture():
    regions = pd.DataFrame({
        "region_fips": ["17001", "29001"], "region": ["Alpha", "Beta"], "state": ["Illinois", "Missouri"],
        "lat": [39.5, 38.5], "lon": [-90.5, -91.5], "land_km2": [1000.0, 1200.0], "n_counties": [1, 1],
        "customers": [10_000, 50_000], "population": [20_000, 100_000], "housing_units": [9_000, 45_000],
        "housing_per_km2": [9.0, 37.5], "share_homes_pre1960": [0.3, 0.5], "median_year_built": [1975, 1962],
        "canopy_mean_pct": [12.0, 45.0], "canopy_dense_share": [0.1, 0.5],
        "hours_out_per_customer": [3.0, 8.0], "events_per_year": [10.0, 30.0], "storm_hit_rate": [0.05, 0.2],
        "quiet_event_rate": [0.01, 0.03], "median_event_hours": [6.0, 12.0], "repeat_7d_share": [0.3, 0.5],
        "history_start": pd.Timestamp("2020-01-01"), "history_end": pd.Timestamp("2024-01-01"),
        "geojson": [square(-91, 39), square(-92, 38)],
    })
    blocks = pd.date_range("2025-05-15", periods=12, freq="6h")
    preds = pd.DataFrame([
        {"region_fips": f, "block_start": b, "prob": 0.1 * i % 1, "y": int(i == 4), "is_onset": i != 5,
         "peak_out": 100 * i,
         "peak_pct_out": 0.5 * i, "gust_max_ms": 10.0 + i, "cape_max_jkg": 500.0, "precip_sum_mm": 2.0,
         "shear_0_6km_max_ms": 15.0, "storm_reports": int(i == 4), "storm_max_wind_kt": None, "storm_tornado": 0}
        for f in ["17001", "29001"] for i, b in enumerate(blocks)
    ])
    storms = (preds.groupby("block_start")
                   .agg(customers_out=("peak_out", "sum"), regions_hit=("y", "sum"), mean_prob=("prob", "mean"),
                        reports=("storm_reports", "sum"))
                   .reset_index().sort_values("customers_out", ascending=False))
    metrics = pd.DataFrame([
        {"benchmark": "quick", "threshold_pct": thr, "train_on": "all", "split": label, "split_kind": kind,
         "model": model, "features": f, "params": "{}", "fit_seconds": 1.0, "git_commit": "abc1234",
         **{f"{pre}{k}": v for pre in ("", "onset_") for k, v in
            {"pr_auc": 0.1, "pr_auc_lift": 10.0, "roc_auc": 0.8, "brier": 0.01, "log_loss": 0.05,
             "precision_top1": 0.1, "recall_top1": 0.1, "event_rate": 0.01, "n_test": 100, "n_events": 1}.items()}}
        for thr in (1, 5, 10)
        for kind, label in [("time", "time(train_years=[2024],test_years=[2025])"), ("county", "county(folds=5)")]
        for model, f in [("prior", "-"), ("climatology", "-"), ("lightgbm", "weather"),
                         ("lightgbm", "weather+place+history+recent")]
    ])
    importance = pd.DataFrame({"scored_on": ["new outages", "new outages", "all blocks", "all blocks"],
                               "feature": ["gust_max_ms", "canopy_mean_pct"] * 2,
                               "importance": [0.05, 0.01, 0.04, 0.02], "std": [0.01, 0.005, 0.01, 0.005]})
    yearly = pd.DataFrame([{"region_fips": f, "year": y, "hours_out_per_customer": 2.0 + k, "events": 10 + k,
                             "worst_pct_out": 5.0 * k}
                            for f in ["17001", "29001"] for k, y in enumerate(range(2020, 2026))])
    for name, df in {"regions": regions, "predictions": preds, "storms": storms,
                     "metrics": metrics, "importance": importance, "yearly": yearly}.items():
        df.to_parquet(APP_DATA / f"{name}.parquet", index=False)
    (APP_DATA / "meta.json").write_text(json.dumps({
        "exported_at": "2026-01-01T00:00:00+00:00", "features": "weather+place+history+recent", "feature_list": [],
        "model": "lightgbm", "config": "ml/benchmarks/quick.yaml", "alert_threshold": 0.1, "alert_precision": 0.2,
        "threshold_pct": 5.0, "train_year": 2024, "test_year": 2025, "n_regions": 2,
        "test_events": 2, "test_blocks": 24, "onset_alert_threshold": 0.3,
    }))
    # the hourly tables (ml/export_hourly.py)
    headline, newest, official = "With HRRR forecasts (mean of 5 runs)", "With HRRR forecasts (newest run)", \
        "Warnings + outlook"
    hours = pd.date_range("2025-05-16 00:00", periods=30, freq="h")
    pd.DataFrame([
        {"region_fips": f, "hour": h, "pct_out": float(i % 9), "customers": c, "out": c * (i % 9) / 100,
         "p_mean": 0.02 * (i % 10), "p_low": 0.01 * (i % 10), "p_high": 0.03 * (i % 10), "new_outage": i == 8,
         "storm": 0, "peak": hours[15], "customers_out_peak": 5000.0}
        for f, c in [("17001", 10_000), ("29001", 50_000)] for i, h in enumerate(hours)
    ]).to_parquet(APP_DATA / "hourly_storms.parquet", index=False)
    shares = [0.001, 0.0075, 0.02]
    pd.DataFrame([
        {"model": model, "alert_share": sh, "actual_share": sh * k, "caught": 0.1 + sh * 10 * k, "precision": 0.15,
         "episodes": 1000 * sh * 100, **{f"net_cut{c}_cost{w}k": 1e6 * c / w for c in (10, 25) for w in (5, 20)}}
        for model, k in [(headline, 1), (newest, 1.1), (official, 0.4)] for sh in shares
    ]).to_parquet(APP_DATA / "alert_curves.parquet", index=False)
    pd.DataFrame({"region_fips": ["17001", "29001"], "expected": [3.0, 5.0], "actual": [2, 6],
                  "mean_probability": [0.004, 0.006], "new_outages": [4.0, 1.0], "caught": [1.0, 0.0],
                  "caught_share": [0.25, 0.0]}).to_parquet(APP_DATA / "county_hourly.parquet", index=False)
    pd.DataFrame({"bin": ["(0, 0.01]", "(0.01, 1]"], "decisions": [1000, 50], "mean_probability": [0.002, 0.1],
                  "outage_share": [0.002, 0.09], "range_low": [0.001, 0.06], "range_high": [0.003, 0.15]}) \
        .to_parquet(APP_DATA / "calibration.parquet", index=False)
    pd.DataFrame({"day": pd.to_datetime(["2025-05-16", "2025-03-14"]), "new_outages": [5, 3], "counties": [2, 2],
                  "caught_model": [3, 2], "caught_official": [1, 2], "customers_out_peak": [5000.0, 9000.0]}) \
        .to_parquet(APP_DATA / "storm_days.parquet", index=False)
    (APP_DATA / "meta_hourly.json").write_text(json.dumps({
        "test_year": 2025, "lead_hours": 2, "threshold_pct": 5, "headline_model": headline, "headline_share": 0.0075,
        "alert_level": 0.1, "n_decisions": 60, "n_new_outages": 8, "event_rate": 0.005,
        "ladder": {headline: {"onset_pr_auc": 0.1, "lo": 0.05, "hi": 0.15, "ratio_vs_official": 2.5,
                              "ratio_vs_official_lo": 2.1, "ratio_vs_official_hi": 3.4}},
        "at_headline_share": {m: {"caught": 0.3, "precision": 0.16, "episodes": 3000}
                              for m in (headline, newest, official)},
    }))
    (APP_DATA / "states.json").write_text(json.dumps([
        {"name": s, "type": "Feature", "geometry": json.loads(square(x, y))}
        for s, x, y in [("Illinois", -91, 39), ("Missouri", -92, 38)]]))


write_fixture()
