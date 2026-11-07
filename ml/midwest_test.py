"""The headline test with Iowa, Indiana and Michigan added (MO, IL, IA, IN, MI; dbt/seeds/study_states.csv).

All weather comes from NOAA's HRRR GRIB archive (ingest/fetch_hrrr_grib.py, ingest/grib_to_study.py): forecast
hour 1 as the actual weather for training, and the five runs issued 2-6 hours before each decision for 2025,
as the headline. Two trainings, each with its own warnings + outlook baseline trained on the same rows:

  MO+IL   trained on Missouri and Illinois only: scored on MO+IL it checks the new weather source against the
          headline (2.40x), and scored on IA+IN+MI it is a model used in states it never saw
  all 5   trained on all five states

Each is scored on MO+IL, on IA+IN+MI, on all five, and state by state: PR-AUC with storm-day ranges, the ratio
to warnings + outlook, and alerts on the riskiest 0.75% of county-hours (as the headline).

Usage: pixi run python -m ml.midwest_test
Writes ml/results/midwest_2025.csv
"""
import numpy as np
import pandas as pd

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import EQUAL_SHARE, LEAD, WINDOW, forecasts, tables, window_from_forecast
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, caught_flags, episodes, onset_hours
from ml.place_extra import NAMES, five_run_mean
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

STATES = data.STATE_ABBR
FIRST = ["MO", "IL"]                                       # the study's first two states
NEW = [s for s in STATES.values() if s not in FIRST]
ALL = f"all {len(STATES)}"
GROUPS = {"MO+IL": FIRST, "+".join(NEW): NEW, ALL: list(STATES.values()), **{s: [s] for s in STATES.values()}}
TRAININGS = {"MO+IL": FIRST, ALL: list(STATES.values())}
OFFICIAL = "warnings + outlook"
OUT = data.ROOT / "ml" / "results" / "midwest_2025.csv"


def state(fips):
    return fips.str[:2].map(STATES)


def main():
    f = forecasts("2024-12-31", "2025-12-31")
    train, _, _, test = tables({n: window_from_forecast(f, k) for n, k in zip(NAMES, RUN_AGES, strict=True)})
    del f
    train["state"], test["state"] = state(train.region_fips), state(test.region_fips)
    base = data.resolve_features(FEATURES) + WINDOW
    official = models.NEEDS_COLUMNS["official"]
    pred = test[["region_fips", "state", "block_start", "y"]].copy()
    for name, states in TRAININGS.items():
        rows = train[train.state.isin(states)]
        print(f"training on {name}: {len(rows):,} rows, {int(rows.y.sum()):,} positives", flush=True)
        pred[f"{OFFICIAL} ({name})"] = models.build("official").fit(rows[official], rows["y"]).predict_proba(
            test[official])[:, 1]
        model = models.build("xgboost", PARAMS).fit(rows[base], rows["y"])
        pred[f"model ({name})"] = five_run_mean(model, test, base)
    pred.to_parquet(data.ROOT / "data" / "cache" / "midwest_2025_predictions.parquet", index=False)

    onsets = onset_hours(2025)
    onsets["state"] = state(onsets.region_fips.astype(str))
    first = storm_day(pd.Series([pd.Timestamp("2024-12-31")]))[0]
    results = []
    for group, states in GROUPS.items():
        p = pred[pred.state.isin(states)]
        o = onsets[onsets.state.isin(states)]
        row_day = ((storm_day(p.block_start) - first).dt.days).to_numpy()
        onset_day = ((storm_day(o.hour) - first).dt.days).to_numpy()
        counts, _ = day_weights(np.arange(max(row_day.max(), onset_day.max()) + 1))
        for name in TRAININGS:
            auc = {k: pr_auc_resamples(p.y, p[f"{k} ({name})"], row_day, counts) for k in (OFFICIAL, "model")}
            r = {"scored_on": group, "trained_on": name, "counties": p.region_fips.nunique(),
                 "new_outages": len(o)}
            for k in (OFFICIAL, "model"):
                s = p[f"{k} ({name})"].to_numpy()
                tag = "official" if k == OFFICIAL else "model"
                r[f"{tag}_pr_auc"] = score(p.y, s)["pr_auc"]
                flagged = pd.Series(s > np.quantile(s, 1 - EQUAL_SHARE), index=p.index)
                hit = np.array(caught_flags(p, flagged, o, LEAD), dtype=float)
                r[f"{tag}_caught"], r[f"{tag}_precision"] = hit.mean(), p.y[flagged].mean()
                r[f"{tag}_caught_lo"], r[f"{tag}_caught_hi"] = interval(
                    weighted_mean_resamples(hit, onset_day, counts))
                r[f"{tag}_spells"] = episodes(p, flagged)
            r["ratio"] = r["model_pr_auc"] / r["official_pr_auc"]
            r["ratio_lo"], r["ratio_hi"] = interval(auc["model"] / auc[OFFICIAL])
            r["better_share"] = float(np.mean(auc["model"] > auc[OFFICIAL]))
            results.append(r)
            print({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()}, flush=True)
    pd.DataFrame(results).to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
