"""The headline model without live outage data (docs/experiments.md, E43).

A live test can get HRRR forecasts, NWS warnings and SPC outlooks as they are issued, but not current outages:
EAGLE-I is published about a year later, and the utilities' outage maps don't allow automated collection. Four
inputs come from outage data: the county's share out at the decision and its worst share in the past 24 hours,
and the worst neighbouring and upwind county at the decision. This retrains the headline model (mean of the
five HRRR runs issued 2-6 hours before) without them and scores both on the same 2025 decisions: PR-AUC on fresh
new outages 2 hours ahead with a paired storm-day range, and alerts on each one's riskiest 0.75% of county-hours.

Usage: pixi run python -m ml.live_inputs
Writes ml/results/live_inputs_2025.csv.
"""
import numpy as np
import pandas as pd

from ml import data, models
from ml.forecast_test import (
    EQUAL_SHARE,
    LEAD,
    TEST_YEAR,
    WINDOW,
    fit_versions,
    official_counts,
    predict_five_runs,
    train_rows,
)
from ml.metrics import score
from ml.moving_window import FEATURES, caught_flags, episodes, onset_hours
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

OUTAGE_INPUTS = ["pct_out_now", "max_pct_out_prev_24h", "near_pct_out_max", "up_pct_out_max"]


def main():
    full = data.resolve_features(FEATURES) + WINDOW
    versions = {
        "warnings + outlook": ("official", models.NEEDS_COLUMNS["official"]),
        "headline (all inputs)": ("xgboost", full),
        "without live outage data": ("xgboost", [c for c in full if c not in OUTAGE_INPUTS]),
    }
    # sampled training, exact rate table, 2025 a state at a time; models with window weather get the five-run mean
    train = train_rows()
    fitted = fit_versions(versions, train, official_counts()[0])
    del train
    pred = predict_five_runs(fitted)

    onsets = onset_hours(TEST_YEAR)
    first = storm_day(pd.Series([pd.Timestamp(f"{TEST_YEAR - 1}-12-31")]))[0]
    row_day = ((storm_day(pred.block_start) - first).dt.days).to_numpy()
    onset_day = ((storm_day(onsets.hour) - first).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(max(row_day.max(), onset_day.max()) + 1))
    auc = {n: pr_auc_resamples(pred.y, pred[n], row_day, counts) for n in versions}
    rows = []
    for n in versions:
        p = pred[n].to_numpy()
        r = {"model": n, "onset_pr_auc": score(pred.y, p)["pr_auc"]}
        r["onset_pr_auc_lo"], r["onset_pr_auc_hi"] = interval(auc[n])
        for ref in ("warnings + outlook", "headline (all inputs)"):
            if n != ref:
                r[f"ratio_vs_{ref}"] = r["onset_pr_auc"] / score(pred.y, pred[ref])["pr_auc"]
                r[f"ratio_vs_{ref}_lo"], r[f"ratio_vs_{ref}_hi"] = interval(auc[n] / auc[ref])
                r[f"better_vs_{ref}"] = float(np.mean(auc[n] > auc[ref]))
        flagged = pd.Series(p > np.quantile(p, 1 - EQUAL_SHARE), index=pred.index)
        hit = np.array(caught_flags(pred, flagged, onsets, LEAD), dtype=float)
        r["alert_share"], r["precision"] = flagged.mean(), pred.y[flagged].mean()
        r["precision_lo"], r["precision_hi"] = interval(
            weighted_mean_resamples(pred.y[flagged], row_day[flagged.to_numpy()], counts))
        r["caught"] = hit.mean()
        r["caught_lo"], r["caught_hi"] = interval(weighted_mean_resamples(hit, onset_day, counts))
        r["episodes"] = episodes(pred, flagged)
        rows.append(r)
        print({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()}, flush=True)
    pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / "live_inputs_2025.csv", index=False)


if __name__ == "__main__":
    main()
