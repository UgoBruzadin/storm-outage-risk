"""A probability range for each decision, from several HRRR runs (docs/experiments.md, E21).

At a decision hour h, the HRRR runs issued 2, 3, 4, 5 and 6 hours before h all forecast the
window it asks about (h + LEAD ... h + LEAD + 5), each with its own errors: a "time-lagged
ensemble". The forecast_test.py model (trained on actual weather) is fed each run in turn, which
gives five probabilities per decision. Their lowest and highest are the range; their mean is
also scored as a forecast of its own.

Checks:
  members     onset PR-AUC of each run age, and of the mean of all five (storm-day ranges)
  bins        decisions grouped by the mean probability: the share that had an outage, next to
              the mean probability and the average range. Well calibrated = outage share ~ mean
  spread      within the same probability bin, do decisions with a wide range behave differently
              from those with a narrow one? (if not, the range carries no information)

Usage: pixi run python -m ml.forecast_ensemble
Writes ml/results/forecast_ensemble_2025.csv (members), forecast_ensemble_bins_2025.csv, and the
per-decision range to data/cache/forecast_ensemble_2025.parquet.
"""
import numpy as np
import pandas as pd

from ml import data, models
from ml.forecast_test import TEST_YEAR, WINDOW, forecasts, tables, window_from_forecast, with_version
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

RUN_AGES = [2, 3, 4, 5, 6]               # forecast hours up to 6 + 2 + 5 = 13, the most stored
BINS = [0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1]
RESULTS = data.ROOT / "ml" / "results"


def main():
    f = forecasts(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31")
    names = [f"run {k} h before" for k in RUN_AGES]
    train, _, _, test = tables({n: window_from_forecast(f, k) for n, k in zip(names, RUN_AGES, strict=True)})
    features = data.resolve_features(FEATURES) + WINDOW
    fitted = models.build("xgboost", PARAMS).fit(train[features], train["y"])
    probs = np.column_stack([fitted.predict_proba(with_version(test, features, n))[:, 1] for n in names])

    out = test[["region_fips", "block_start", "y"]].copy()
    out["p_mean"], out["p_low"], out["p_high"] = probs.mean(axis=1), probs.min(axis=1), probs.max(axis=1)
    out["p_newest"] = probs[:, 0]
    out.to_parquet(data.ROOT / "data" / "cache" / "forecast_ensemble_2025.parquet", index=False)

    first = pd.Timestamp(f"{TEST_YEAR - 1}-12-31")
    row_day = (storm_day(out.block_start) - first).dt.days.to_numpy()
    counts, _ = day_weights(np.arange(row_day.max() + 1))
    auc = {n: pr_auc_resamples(out.y, probs[:, i], row_day, counts) for i, n in enumerate(names)}
    auc["mean of the 5 runs"] = pr_auc_resamples(out.y, out.p_mean, row_day, counts)
    columns = {n: probs[:, i] for i, n in enumerate(names)} | {"mean of the 5 runs": out.p_mean.to_numpy()}
    rows = []
    for n, p in columns.items():
        r = {"forecast": n, "onset_pr_auc": score(out.y, p)["pr_auc"]}
        r["onset_pr_auc_lo"], r["onset_pr_auc_hi"] = interval(auc[n])
        r["diff_vs_newest_lo"], r["diff_vs_newest_hi"] = interval(auc[n] - auc[names[0]])
        rows.append(r)
        print({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()}, flush=True)
    pd.DataFrame(rows).to_csv(RESULTS / "forecast_ensemble_2025.csv", index=False)

    out["bin"] = pd.cut(out.p_mean, BINS, include_lowest=True)
    out["width"] = out.p_high - out.p_low
    out["wide"] = out.width > out.groupby("bin", observed=True).width.transform("median")
    bins = out.groupby("bin", observed=True).agg(
        decisions=("y", "size"), mean_probability=("p_mean", "mean"), outage_share=("y", "mean"),
        range_low=("p_low", "mean"), range_high=("p_high", "mean"))
    spread = out.groupby(["bin", "wide"], observed=True).y.mean().unstack()
    bins["outage_share_narrow_range"], bins["outage_share_wide_range"] = spread[False], spread[True]
    bins.to_csv(RESULTS / "forecast_ensemble_bins_2025.csv")
    print(bins.round(4).to_string())


if __name__ == "__main__":
    main()
