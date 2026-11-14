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
from ml.forecast_test import EQUAL_SHARE, LEAD, TRAIN_YEARS, WINDOW, states_2025, train_rows, window_from_forecast
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT, caught_flags, episodes, onset_hours
from ml.place_extra import NAMES, five_run_mean
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

FIRST = ["MO", "IL"]                                       # the study's first two states
OFFICIAL = "warnings + outlook"
OUT = data.ROOT / "ml" / "results" / "midwest_2025.csv"


def study_groups():
    """The groups scored and the trainings, for the states the warehouse holds (not just the seed's list)."""
    states = [data.STATE_ABBR.get(s, s) for s in data.warehouse_states()]
    new = [s for s in states if s not in FIRST]
    every = f"all {len(states)}"
    new_name = "+".join(new) if len(new) <= 5 else f"the other {len(new)}"
    groups = {"MO+IL": FIRST, new_name: new, every: states, **{s: [s] for s in states}}
    return groups, {"MO+IL": FIRST, every: states}


def state(fips):
    return fips.astype(str).str[:2].map(data.STATE_ABBR)


def main():
    groups, trainings = study_groups()
    base = data.resolve_features(FEATURES) + WINDOW
    official = models.NEEDS_COLUMNS["official"]
    # the rate table's counts over the full training table, by county, so each training's table is exact
    counts = data.hourly_counts(THRESHOLD_PCT, TRAIN_YEARS, LEAD, official + ["region_fips"])
    counts["state"] = state(counts.region_fips)
    train = train_rows()
    train["state"] = state(train.region_fips)
    fitted = {}
    for name, states in trainings.items():
        rows, c = train[train.state.isin(states)], counts[counts.state.isin(states)]
        print(f"training on {name}: {len(rows):,} rows standing for {rows.weight.sum():,.0f}, "
              f"{int(rows.y.sum()):,} positives", flush=True)
        fitted[name] = (models.build("official").fit(c[official], c.y, sample_weight=c.weight),
                        models.build("xgboost", PARAMS).fit(rows[base], rows.y, sample_weight=rows.weight))
    del train, counts

    parts = []
    for _, test, _ in states_2025(lambda f: {n: window_from_forecast(f, k) for n, k in
                                             zip(NAMES, RUN_AGES, strict=True)}):
        p = test[["region_fips", "block_start", "y"]].copy()
        p["state"] = state(p.region_fips)
        for name, (off, model) in fitted.items():
            p[f"{OFFICIAL} ({name})"] = off.predict_proba(test[official])[:, 1]
            p[f"model ({name})"] = five_run_mean(model, test, base)
        parts.append(p)
        del test
    pred = pd.concat(parts, ignore_index=True)
    pred.to_parquet(data.ROOT / "data" / "cache" / "midwest_2025_predictions.parquet", index=False)

    onsets = onset_hours(2025)
    onsets["state"] = state(onsets.region_fips.astype(str))
    first = storm_day(pd.Series([pd.Timestamp("2024-12-31")]))[0]
    results = []
    for group, states in groups.items():
        p = pred[pred.state.isin(states)]
        o = onsets[onsets.state.isin(states)]
        if p.empty or o.empty or p.y.sum() == 0:
            print(f"{group}: nothing to score, skipped", flush=True)
            continue
        row_day = ((storm_day(p.block_start) - first).dt.days).to_numpy()
        onset_day = ((storm_day(o.hour) - first).dt.days).to_numpy()
        counts, _ = day_weights(np.arange(max(row_day.max(), onset_day.max()) + 1))
        for name in trainings:
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
