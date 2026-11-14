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
import pandas as pd

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import WINDOW, states_2025, train_rows, window_from_forecast, with_version
from ml.moving_window import FEATURES, PARAMS


def main():
    # every county-hour (ongoing outages included), sampled for training like the scored model
    train = train_rows(onsets_only=False)
    features = data.resolve_features(FEATURES) + WINDOW
    fitted = models.build("xgboost", PARAMS).fit(train[features], train["y"], sample_weight=train["weight"])
    print(f"trained on {len(train):,} county-hours standing for {train.weight.sum():,.0f} (ongoing outages "
          f"included)", flush=True)
    del train

    names = [f"run {k} h before" for k in RUN_AGES]
    parts = []
    for _, _, test in states_2025(lambda f: {n: window_from_forecast(f, k) for n, k in
                                             zip(names, RUN_AGES, strict=True)}, onsets=False, every=True):
        probs = np.column_stack([fitted.predict_proba(with_version(test, features, n))[:, 1] for n in names])
        out = test[["region_fips", "block_start"]].copy()
        out["p_mean"], out["p_low"], out["p_high"] = probs.mean(axis=1), probs.min(axis=1), probs.max(axis=1)
        parts.append(out)
        del test
    out = pd.concat(parts, ignore_index=True)
    out.to_parquet(data.ROOT / "data" / "cache" / "display_2025.parquet", index=False)
    print(f"wrote {len(out):,} county-hours of 2025", flush=True)


if __name__ == "__main__":
    main()
