"""Calibrate the headline model's probabilities on 2024, with 2024's HRRR forecasts (docs/experiments.md, E27).

The headline model (forecast_ensemble.py: trained on actual weather, fed the mean of the five HRRR runs issued
2-6 hours before each decision) ranks well, but above ~20% its probabilities run high (E21): it takes forecasts
as literally as observations. The dollar rule (stage when probability x expected loss >= cost) needs the
probabilities themselves to be right, so its estimate so far used the model without forecasts.

  1. validation model: the headline model trained on 2020-2023, run on 2024 with 2024's forecasts, as it
     would have run live
  2. on 2024: an isotonic map from its probability to how often a new outage followed, and an alert level
     frozen as its top HEADLINE_SHARE of 2024 hours
  3. on 2025 (the headline model trained on 2020-2024): calibrated probabilities, calibration before and
     after, onset PR-AUC before and after (the map keeps the order, up to ties), alerts at the frozen level
  4. the dollar estimate (value_hourly.py's rule, scenarios and outages) for the calibrated headline model

Usage: pixi run python -m ml.calibrate_forecasts
Writes ml/results/calibration_forecasts_2025.csv, value_forecasts_2025.csv, and the calibrated 2025
probabilities to data/cache/forecast_calibrated_2025.parquet.
"""
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score

from ml import data, models
from ml.export_hourly import HEADLINE_SHARE
from ml.forecast_ensemble import BINS, RUN_AGES
from ml.forecast_test import LEAD, WINDOW, states_2025, train_rows, window_from_forecast, with_version
from ml.moving_window import FEATURES, PARAMS, caught_flags, episodes, onset_hours
from ml.value import MIXES, RESTORATION_CUT, STAGING_COST
from ml.value_hourly import avoidable, net_savings, outages

VAL_TRAIN, VAL_YEAR, TEST_YEAR = [2020, 2021, 2022, 2023], 2024, 2025
NAMES = [f"run {k} h before" for k in RUN_AGES]
RESULTS = data.ROOT / "ml" / "results"


def validation_probabilities():
    """The headline model trained on 2020-2023, fed 2024's five HRRR runs: its 2024 probabilities."""
    train = train_rows(VAL_TRAIN)                         # sampled, as the headline model's training
    features = data.resolve_features(FEATURES) + WINDOW
    fitted = models.build("xgboost", PARAMS).fit(train[features], train["y"], sample_weight=train["weight"])
    del train
    ys, ps = [], []                                       # 2024, every decision (never sampled), a state at a time
    def five_runs(f):
        return {n: window_from_forecast(f, k) for n, k in zip(NAMES, RUN_AGES, strict=True)}

    for _, val, _ in states_2025(five_runs, year=VAL_YEAR, require_actual=False):
        ps.append(np.column_stack([fitted.predict_proba(with_version(val, features, n))[:, 1] for n in NAMES])
                  .mean(axis=1))
        ys.append(val.y.to_numpy())
        del val
    y, p = np.concatenate(ys), np.concatenate(ps)
    print(f"2024: {len(y):,} decisions, {int(y.sum()):,} positive windows", flush=True)
    return y, p


def bins(y, p):
    d = pd.DataFrame({"y": y, "p": p, "bin": pd.cut(p, BINS, include_lowest=True)})
    return d.groupby("bin", observed=True).agg(decisions=("y", "size"), predicted=("p", "mean"),
                                               observed=("y", "mean"))


def main():
    y24, p24 = validation_probabilities()
    iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(p24, y24)
    level = float(np.quantile(p24, 1 - HEADLINE_SHARE))            # alert level frozen on 2024 forecasts

    test = pd.read_parquet(data.ROOT / "data" / "cache" / "forecast_ensemble_2025.parquet")
    test["p_cal"] = iso.predict(test.p_mean)
    test.to_parquet(data.ROOT / "data" / "cache" / "forecast_calibrated_2025.parquet", index=False)
    before, after = bins(test.y, test.p_mean), bins(test.y, test.p_cal)
    table = before.join(after, lsuffix="_raw", rsuffix="_calibrated")
    table.to_csv(RESULTS / "calibration_forecasts_2025.csv")
    print(table.round(4).to_string(), flush=True)

    onsets = onset_hours(TEST_YEAR)
    flagged = pd.Series(test.p_mean.to_numpy() > level, index=test.index)
    print({"pr_auc_raw": round(average_precision_score(test.y, test.p_mean), 4),
           "pr_auc_calibrated": round(average_precision_score(test.y, test.p_cal), 4),
           "level_2024": round(level, 4), "alert_share_2025": round(float(flagged.mean()), 4),
           "precision": round(float(test.y[flagged].mean()), 4),
           "caught": round(float(np.mean(caught_flags(test, flagged, onsets, LEAD))), 4),
           "spells": episodes(test, flagged)}, flush=True)

    # the dollar estimate: value_hourly.py's rule on the calibrated headline probabilities
    train_ev = outages([2020, 2021, 2022, 2023, 2024])
    test_ev = outages([TEST_YEAR]).reset_index(drop=True)
    rows = []
    for mix_name, mix in MIXES.items():
        for cut in RESTORATION_CUT:
            for cost in STAGING_COST:
                per_region = train_ev.assign(v=avoidable(train_ev, mix, cut)).groupby("region_fips").v.mean()
                expected = test.region_fips.map(per_region).fillna(per_region.mean())
                saved = avoidable(test_ev, mix, cut)
                row = {"mix": mix_name, "restoration_cut": cut, "staging_cost": cost}
                for name, col in (("forecast_calibrated", "p_cal"), ("forecast_raw", "p_mean")):
                    row[name], row[f"{name}_episodes"] = net_savings(test, test[col] * expected >= cost,
                                                                     test_ev, saved, cost)
                rows.append(row)
                print({k: round(v / 1e6, 2) if isinstance(v, float) and abs(v) > 1000 else v
                       for k, v in row.items()}, flush=True)
    pd.DataFrame(rows).to_csv(RESULTS / "value_forecasts_2025.csv", index=False)


if __name__ == "__main__":
    main()
