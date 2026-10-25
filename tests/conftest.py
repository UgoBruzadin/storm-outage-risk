"""Shared test setup: a tiny fake app dataset, so tests never need the real data.

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
sys.path.insert(0, str(ROOT / "app"))          # pages do `from lib import ...`

APP_DATA = Path(tempfile.mkdtemp(prefix="app-data-"))
os.environ["APP_DATA"] = str(APP_DATA)


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
        {"region_fips": f, "block_start": b, "prob": 0.1 * i % 1, "y": int(i == 4), "peak_out": 100 * i,
         "peak_pct_out": 0.5 * i, "gust_max_ms": 10.0 + i, "cape_max_jkg": 500.0, "precip_sum_mm": 2.0,
         "shear_0_6km_max_ms": 15.0, "storm_reports": int(i == 4), "storm_max_wind_kt": None, "storm_tornado": 0}
        for f in ["17001", "29001"] for i, b in enumerate(blocks)
    ])
    storms = (preds.groupby("block_start")
                   .agg(customers_out=("peak_out", "sum"), regions_hit=("y", "sum"), mean_prob=("prob", "mean"),
                        reports=("storm_reports", "sum"))
                   .reset_index().sort_values("customers_out", ascending=False))
    metrics = pd.DataFrame([
        {"split": s, "model": "hgb", "features": f, "pr_auc": 0.1, "roc_auc": 0.8, "brier": 0.01,
         "event_rate": 0.01, "n_test": 100, "n_events": 1, "threshold_pct": 5.0}
        for s in ["time", "county", "random"]
        for f in ["weather", "weather+place", "weather+place-canopy", "weather+place+history"]
    ])
    importance = pd.DataFrame({"feature": ["gust_max_ms", "canopy_mean_pct"], "importance": [0.05, 0.01],
                               "std": [0.01, 0.005]})
    for name, df in {"regions": regions, "predictions": preds, "storms": storms,
                     "metrics": metrics, "importance": importance}.items():
        df.to_parquet(APP_DATA / f"{name}.parquet", index=False)
    (APP_DATA / "meta.json").write_text(json.dumps({
        "exported_at": "2026-01-01T00:00:00+00:00", "features": "weather+place+history", "feature_list": [],
        "threshold_pct": 5.0, "train_year": 2024, "test_year": 2025, "n_regions": 2,
        "test_events": 2, "test_blocks": 24,
    }))


write_fixture()
