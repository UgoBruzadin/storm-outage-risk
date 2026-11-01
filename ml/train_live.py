"""Train the frozen model for the live forecast (live/README.md).

The headline recipe (docs/experiments.md, E21, E43): XGBoost with the final settings, trained on the window's actual
weather and fed the mean of the five latest HRRR runs when it predicts; without the four outage inputs, which a
live job can't get. Trained on fresh new outages of 2020-2025, 2 hours ahead.

An alert level is a probability cut-off, so it belongs to one model. Two are saved for the pre-registration to
choose from: the share-based level of the same recipe trained on 2020-2024 and run on 2025 with forecasts
(out of sample, but a different model), and the frozen model's own top 0.75% of 2025 hours (in sample).

Usage: pixi run python -m ml.train_live
Writes live/model/model.json (XGBoost) and live/model/meta.json.
"""
import json
from datetime import UTC, datetime

import numpy as np

from live.features import live_features
from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import (
    EQUAL_SHARE,
    LEAD,
    WINDOW,
    actual_hourly,
    forecasts,
    window_from_forecast,
    window_from_hourly,
    with_version,
)
from ml.moving_window import PARAMS, THRESHOLD_PCT

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
OUT = data.ROOT / "live" / "model"


def table(years):
    df = data.load_hourly(THRESHOLD_PCT, years, LEAD)
    df["region_fips"] = df.region_fips.astype(str)
    return df.merge(window_from_hourly(actual_hourly(years)), on=["region_fips", "block_start"], how="left")


def mean_over_runs(fitted, test, features):
    f = forecasts("2024-12-31", "2025-12-31")
    names = [f"run {k} h before" for k in RUN_AGES]
    for n, k in zip(names, RUN_AGES, strict=True):
        w = window_from_forecast(f, k)
        test = test.merge(w.rename(columns={c: f"{c}|{n}" for c in WINDOW}), on=["region_fips", "block_start"],
                          how="left")
    keep = test[[f"win_gust_max_ms|{n}" for n in names]].notna().all(axis=1)
    test = test[keep]
    return np.mean([fitted.predict_proba(with_version(test, features, n))[:, 1] for n in names], axis=0)


def main():
    features = live_features()
    df = table(YEARS)
    train = df[df.year.isin(YEARS)]
    print(f"training rows {len(train):,}, positives {int(train.y.sum()):,}", flush=True)
    final = models.build("xgboost", PARAMS).fit(train[features], train["y"])
    OUT.mkdir(parents=True, exist_ok=True)
    final.save_model(OUT / "model.json")

    test = df[df.year == 2025]
    held_out = models.build("xgboost", PARAMS).fit(df[df.year < 2025][features], df[df.year < 2025]["y"])
    p_held = mean_over_runs(held_out, test, features)
    p_final = mean_over_runs(final, test, features)
    meta = {
        "trained": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "train_years": YEARS, "lead_hours": LEAD, "threshold_pct": THRESHOLD_PCT, "run_ages": RUN_AGES,
        "params": PARAMS, "features": features, "training_rows": len(train), "training_positives": int(train.y.sum()),
        "alert_share": EQUAL_SHARE,
        "alert_level_held_out": float(np.quantile(p_held, 1 - EQUAL_SHARE)),
        "alert_level_in_sample": float(np.quantile(p_final, 1 - EQUAL_SHARE)),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print({k: v for k, v in meta.items() if k not in ("features", "params")})


if __name__ == "__main__":
    main()
