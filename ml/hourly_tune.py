"""A small grid around the 6-hour model's settings for the moving-window model, on the 2024
validation year (trained on 2020–2023) at one lead. Differences under ~2% are seed noise
(hourly_ablation.py), so the current settings stay unless something clearly beats them.

Usage: pixi run python -m ml.hourly_tune [--lead 2]
Writes ml/results/hourly_tune_lead<L>.csv.
"""
import argparse
import itertools

import pandas as pd

from ml import data, models
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT

TRAIN_YEARS, VAL_YEAR = [2020, 2021, 2022, 2023], 2024
GRID = {"max_depth": [4, 6], "min_child_weight": [20, 100], "n_estimators": [800, 1500]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead", type=int, default=2)
    args = parser.parse_args()
    df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [VAL_YEAR], args.lead)
    train, val = df[df.year.isin(TRAIN_YEARS)], df[df.year == VAL_YEAR]
    features = data.resolve_features(FEATURES)
    rows = []
    for values in itertools.product(*GRID.values()):
        params = PARAMS | dict(zip(GRID, values, strict=True))
        model = models.build("xgboost", params).fit(train[features], train["y"])
        s = score(val["y"].to_numpy(), model.predict_proba(val[features])[:, 1])
        rows.append(dict(zip(GRID, values, strict=True))
                    | {"onset_pr_auc": s["pr_auc"], "recall_top1": s["recall_top1"]})
        print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / f"hourly_tune_lead{args.lead}.csv", index=False)
    print(pd.DataFrame(rows).sort_values("onset_pr_auc", ascending=False).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
