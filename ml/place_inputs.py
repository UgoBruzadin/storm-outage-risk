"""The headline model without place data (docs/experiments.md, E45).

Shuffling the place inputs costs the model about a third of its score (E39), which shows it relies on them, not that
they explain its lead over the official forecasts. This retrains the headline model (mean of the five HRRR runs issued
2-6 hours before) without the six place inputs and compares each version with warnings + outlook on the same 2025
decisions: PR-AUC on fresh new outages 2 hours ahead with paired storm-day ranges, and alerts on each one's riskiest
0.75% of county-hours. Two smaller models show what place adds to the official forecasts alone, with no weather.

Usage: pixi run python -m ml.place_inputs
Writes ml/results/place_inputs_2025.csv.
"""
import numpy as np
import pandas as pd

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import EQUAL_SHARE, LEAD, TEST_YEAR, WINDOW, forecasts, tables, window_from_forecast, with_version
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, caught_flags, episodes, onset_hours
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

OFFICIAL, HEADLINE = "warnings + outlook", "headline (all inputs)"


def main():
    f = forecasts(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31")
    names = [f"run {k} h before" for k in RUN_AGES]
    train, _, _, test = tables({n: window_from_forecast(f, k) for n, k in zip(names, RUN_AGES, strict=True)})
    full = data.resolve_features(FEATURES) + WINDOW
    place = data.resolve_features("place")
    versions = {
        OFFICIAL: ("official", models.NEEDS_COLUMNS["official"]),
        "model on warnings + outlook only": ("xgboost", data.resolve_features("warnings+outlook")),
        "model on warnings + outlook + place": ("xgboost", data.resolve_features("warnings+outlook+place")),
        "headline without place": ("xgboost", [c for c in full if c not in place]),
        HEADLINE: ("xgboost", full),
    }
    pred = test[["region_fips", "block_start", "y"]].copy()
    for label, (model, features) in versions.items():
        fitted = models.build(model, PARAMS if model == "xgboost" else None).fit(train[features], train["y"])
        if WINDOW[0] in features:                        # the mean over the five runs, as the headline
            pred[label] = np.mean([fitted.predict_proba(with_version(test, features, n))[:, 1] for n in names], axis=0)
        else:
            pred[label] = fitted.predict_proba(test[features])[:, 1]
        print(label, flush=True)

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
        for ref in (OFFICIAL, HEADLINE):
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
    pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / "place_inputs_2025.csv", index=False)


if __name__ == "__main__":
    main()
