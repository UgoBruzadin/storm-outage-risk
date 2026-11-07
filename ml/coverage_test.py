"""Does the headline hold without the counties the outage data barely covers? (2025, mean of the five HRRR runs)

EAGLE-I misses some utilities, so in some counties nobody is ever recorded out. Coverage = the average share of
hours with anyone out, 2020-2024 (no 2025 data is used to choose counties). The headline model is trained three
ways: on every county, without those under 5%, and without those under 8%. Each training gets its own warnings +
outlook baseline on the same rows. Every model is scored on all counties and on those kept by the strictest cut,
so rows are comparable across trainings. Ranges: storm days resampled (ml/uncertainty.py).

Usage: pixi run python -m ml.coverage_test
Writes ml/results/coverage_2025.csv.
"""
import duckdb
import numpy as np
import pandas as pd

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import EQUAL_SHARE, LEAD, WINDOW, forecasts, tables, window_from_forecast
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, caught_flags, onset_hours
from ml.place_extra import NAMES, five_run_mean
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

CUTS = (0.05, 0.08)
OUT = data.ROOT / "ml" / "results" / "coverage_2025.csv"


def main():
    con = duckdb.connect(str(data.DB), read_only=True)
    cov = con.sql("""SELECT region_fips, avg(typical_share) AS share FROM marts.mart_study__region_coverage
                     WHERE year BETWEEN 2020 AND 2024 GROUP BY 1""").df()
    con.close()
    cov["region_fips"] = cov.region_fips.astype(str)
    every = set(cov.region_fips)
    train_sets = {"all counties": every} | {f"without under {c:.0%}": set(cov.region_fips[cov.share >= c])
                                            for c in CUTS}
    well = set(cov.region_fips[cov.share >= max(CUTS)])
    score_sets = {"all counties": every, f"covered {max(CUTS):.0%}+": well}

    f = forecasts("2024-12-31", "2025-12-31")
    train, _, _, test = tables({n: window_from_forecast(f, k) for n, k in zip(NAMES, RUN_AGES, strict=True)})
    del f
    for t in (train, test):
        t["region_fips"] = t.region_fips.astype(str)
    base = data.resolve_features(FEATURES) + WINDOW
    official = models.NEEDS_COLUMNS["official"]
    pred = test[["region_fips", "block_start", "y"]].copy()
    for name, regions in train_sets.items():
        rows = train[train.region_fips.isin(regions)]
        print(f"training {name}: {rows.region_fips.nunique()} counties, {int(rows.y.sum()):,} positives", flush=True)
        pred[f"off|{name}"] = models.build("official").fit(rows[official], rows.y).predict_proba(test[official])[:, 1]
        pred[f"mod|{name}"] = five_run_mean(models.build("xgboost", PARAMS).fit(rows[base], rows.y), test, base)

    onsets = onset_hours(2025)
    onsets["region_fips"] = onsets.region_fips.astype(str)
    first = storm_day(pd.Series([pd.Timestamp("2024-12-31")]))[0]
    res = []
    for sname, regions in score_sets.items():
        p, o = pred[pred.region_fips.isin(regions)], onsets[onsets.region_fips.isin(regions)]
        row_day = (storm_day(p.block_start) - first).dt.days.to_numpy()
        onset_day = (storm_day(o.hour) - first).dt.days.to_numpy()
        counts, _ = day_weights(np.arange(max(row_day.max(), onset_day.max()) + 1))
        for tname, kept in train_sets.items():
            r = {"scored_on": sname, "trained_on": tname, "counties_trained": len(kept),
                 "counties_scored": len(regions), "new_outages": len(o)}
            aucs = {}
            for k in ("off", "mod"):
                s = p[f"{k}|{tname}"].to_numpy()
                aucs[k] = pr_auc_resamples(p.y, s, row_day, counts)
                r[f"{k}_pr_auc"] = score(p.y, s)["pr_auc"]
                flagged = pd.Series(s > np.quantile(s, 1 - EQUAL_SHARE), index=p.index)
                hit = np.array(caught_flags(p, flagged, o, LEAD), dtype=float)
                r[f"{k}_caught"], r[f"{k}_precision"] = hit.mean(), p.y[flagged].mean()
            r["ratio"] = r["mod_pr_auc"] / r["off_pr_auc"]
            r["ratio_lo"], r["ratio_hi"] = interval(aucs["mod"] / aucs["off"])
            res.append(r)
            print({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()}, flush=True)
    pd.DataFrame(res).to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
