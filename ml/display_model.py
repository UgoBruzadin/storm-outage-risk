"""A display version of the forecast model, for the story page's storm animation only.

The scored model (forecast_ensemble.py) answers "will a NEW outage start in the next 6 hours?", which is the right
test but animates choppily: a county already out has nothing new to predict. This version, with the same inputs
and the same HRRR runs issued 2-6 hours before each decision, answers "will the county be at least 5% out at any
point in the 6 hours starting 2 hours from now?", ongoing outages included, so its map tracks the outage map.
It is never scored or quoted; every number on the pages comes from the scored model.

Usage: pixi run python -m ml.display_model
Writes data/cache/display_2025.parquet: region, decision hour, the mean and range of the five runs' chances.
"""
import numpy as np

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import (
    LEAD,
    TEST_YEAR,
    TRAIN_YEARS,
    WINDOW,
    actual_hourly,
    forecasts,
    window_from_forecast,
    window_from_hourly,
    with_version,
)
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT


def main():
    actual = window_from_hourly(actual_hourly(TRAIN_YEARS + [TEST_YEAR]))
    df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR], LEAD, onsets_only=False)
    df["region_fips"] = df.region_fips.astype(str)
    df = df.merge(actual, on=["region_fips", "block_start"], how="left")
    train, test = df[df.year.isin(TRAIN_YEARS)], df[df.year == TEST_YEAR].copy()
    features = data.resolve_features(FEATURES) + WINDOW
    fitted = models.build("xgboost", PARAMS).fit(train[features], train["y"])
    print(f"trained on {len(train):,} county-hours, all of them (ongoing outages included)", flush=True)

    f = forecasts(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31")
    names = [f"run {k} h before" for k in RUN_AGES]
    for n, k in zip(names, RUN_AGES, strict=True):
        w = window_from_forecast(f, k)
        test = test.merge(w.rename(columns={c: f"{c}|{n}" for c in WINDOW}), on=["region_fips", "block_start"],
                          how="left")
    test = test.dropna(subset=[f"win_gust_max_ms|{n}" for n in names])
    probs = np.column_stack([fitted.predict_proba(with_version(test, features, n))[:, 1] for n in names])
    out = test[["region_fips", "block_start"]].copy()
    out["p_mean"], out["p_low"], out["p_high"] = probs.mean(axis=1), probs.min(axis=1), probs.max(axis=1)
    out.to_parquet(data.ROOT / "data" / "cache" / "display_2025.parquet", index=False)
    print(f"wrote {len(out):,} county-hours of 2025", flush=True)


if __name__ == "__main__":
    main()
