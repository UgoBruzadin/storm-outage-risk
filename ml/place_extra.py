"""Does more place data improve the headline model? (docs/experiments.md, E47)

Adds each new group of county inputs to the headline model (ingest/fetch_treemap.py, fetch_forest_age.py, fetch_soil.py,
fetch_water.py, fetch_flood_zones.py, fetch_utilities.py, fetch_transmission.py), with recent rain and soil tested
together because wet ground is how soil would matter in a storm.

  select  Trained on 2020-2023, actual weather, scored on 2024 with the mean of the five HRRR runs, as the headline:
          each group over seeds 0-4, then on five held-out sets of counties, each tested by a model without them.
  test    Trained on 2020-2024, scored on 2025, as the headline: the current model, the kept groups together, every
          group together, and warnings + outlook, with paired storm-day ranges and alerts on the riskiest 0.75%.

The rule, fixed before any result: a group is kept if it beats the current model in at least 4 of the 5 seeds on 2024
AND on the held-out counties. Only the kept set and the all-groups set are ever scored on 2025.

Usage: pixi run python -m ml.place_extra select | test
Writes ml/results/place_extra_select.csv (resumes if stopped) and place_extra_2025.csv.
"""
import argparse

import numpy as np
import pandas as pd

from ml import data, models
from ml.forecast_test import (
    EQUAL_SHARE,
    LEAD,
    RUN_NAMES,
    WINDOW_V1,
    fit_versions,
    five_run_mean,
    five_runs,
    official_counts,
    predict_five_runs,
    states_2025,
    train_rows,
)
from ml.forecast_test import (
    TRAIN_YEARS as TEST_TRAIN_YEARS,
)
from ml.metrics import score
from ml.moving_window import FEATURES_V1 as FEATURES
from ml.moving_window import PARAMS_V1 as PARAMS
from ml.moving_window import caught_flags, episodes, onset_hours
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

PLACE_DIR = data.ROOT / "data" / "raw" / "place"
FILES = ["treemap", "forest_age", "soil", "water", "flood_zones", "utilities", "transmission"]
RAIN = ["precip_prev_72h_mm", "wind_x_wet_soil"]
SOIL = ["soil_poor_drain_share", "soil_group_d_share", "soil_flood_share", "soil_water_table_cm", "soil_bedrock_cm"]
WET = ["poor_drain_x_rain", "poor_drain_x_wind_rain"]
GROUPS = {
    "tree type": ["tm_share_oak_hickory", "tm_share_elm_ash_cottonwood", "tm_share_softwood", "tm_share_oak_pine",
                  "tm_share_maple_beech", "tm_share_oak_gum_cypress"],
    "tree size": ["tm_height_ft", "tm_diameter_in", "tm_live_per_acre", "tm_basal_area"],
    "dead trees and ash": ["tm_dead_per_acre", "tm_dead_volume", "tm_ash_stem_share"],
    "tree age": ["stand_age_mean", "stand_age_old"],
    "soil": SOIL,
    "recent rain": RAIN,
    "soil + recent rain": SOIL + RAIN + WET,
    "rivers and streams": ["water_share", "river_near_share", "stream_km_per_km2"],
    "flood zones": ["flood_zone_share"],
    "utilities": ["util_count", "util_share_iou", "util_share_coop", "util_share_public", "util_saidi", "util_saifi",
                  "util_saidi_med"],
    "transmission lines": ["transmission_km_per_km2", "transmission_hv_km_per_km2"],
}
ALL = "every group"
BASE = "current model"
SEEDS = range(5)
FOLDS = 5
TRAIN_YEARS, VAL_YEAR = [2020, 2021, 2022, 2023], 2024
RESULTS = data.ROOT / "ml" / "results"
SELECT_OUT = RESULTS / "place_extra_select.csv"
NAMES = RUN_NAMES                                 # the five runs (other scripts import these two from here)
__all__ = ["NAMES", "five_run_mean"]


def add_place(df):
    """Join the new county inputs onto the modeling rows. The files cover the states they were fetched for
    (ingest/fetch_<source>.py); counties outside them get NaN."""
    df["region_fips"] = df.region_fips.astype(str)
    for name in FILES:
        place = pd.read_csv(PLACE_DIR / f"{name}.csv", dtype={"region_fips": str})
        df = df.drop(columns=[c for c in place if c != "region_fips" and c in df])   # data.add_static joined them
        df = df.merge(place, on="region_fips", how="left")
    df["poor_drain_x_rain"] = df.soil_poor_drain_share * df.precip_prev_72h_mm
    df["poor_drain_x_wind_rain"] = df.soil_poor_drain_share * df.wind_x_wet_soil
    return df


def all_groups():
    return list(dict.fromkeys(c for g in GROUPS.values() for c in g))


def features_for(base, group):
    extra = [] if group == BASE else all_groups() if group == ALL else GROUPS[group]
    return base + [c for c in extra if c not in base]


def select():
    """Group by group (it resumes): the seed models and the held-out-county models are fitted on the sampled
    2020-2023 rows, then 2024 (every decision with all five runs) is scored in one pass over the states."""
    train = add_place(train_rows(TRAIN_YEARS))
    base = data.resolve_features(FEATURES) + WINDOW_V1   # E47 ran on the MO + IL recipe
    rows = pd.read_csv(SELECT_OUT).to_dict("records") if SELECT_OUT.exists() else []
    done = {(r["group"], r["setup"], r["seed"]) for r in rows}

    def record(group, setup, seed, y, p):
        s = score(y, p)
        rows.append({"group": group, "setup": setup, "seed": seed, "onset_pr_auc": s["pr_auc"],
                     "n_inputs_added": len(features_for(base, group)) - len(base)})
        print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(SELECT_OUT, index=False)

    # sorted by reversed code, so neighbouring counties land in different folds
    regions = sorted(train.region_fips.unique(), key=lambda fips: fips[::-1])
    fold_of = {fips: i % FOLDS for i, fips in enumerate(regions)}
    for group in [BASE, *GROUPS, ALL]:
        features = features_for(base, group)
        seeds = [s for s in SEEDS if (group, "2024", s) not in done]
        held_out = (group, "held-out counties", 0) not in done
        if not seeds and not held_out:
            continue
        by_seed = {s: models.build("xgboost", PARAMS | {"random_state": s}).fit(
            train[features], train.y, sample_weight=train.weight) for s in seeds}
        by_fold = {}
        if held_out:
            for fold in range(FOLDS):
                t = train[train.region_fips.map(fold_of) != fold]
                by_fold[fold] = models.build("xgboost", PARAMS | {"random_state": 0}).fit(
                    t[features], t.y, sample_weight=t.weight)
        ys, ps, held = [], {s: [] for s in seeds}, []
        for _, val, _ in states_2025(five_runs, year=VAL_YEAR, require_actual=False):
            val = add_place(val)
            ys.append(val.y.to_numpy())
            for s, m in by_seed.items():
                ps[s].append(five_run_mean(m, val, features))
            if held_out:
                fold = val.region_fips.map(fold_of).fillna(-1).to_numpy()
                p = np.zeros(len(val))
                for k, m in by_fold.items():
                    if (fold == k).any():
                        p[fold == k] = five_run_mean(m, val[fold == k], features)
                held.append(p)
            del val
        y = np.concatenate(ys)
        for s in seeds:
            record(group, "2024", s, y, np.concatenate(ps[s]))
        if held_out:
            record(group, "held-out counties", 0, y, np.concatenate(held))
    print(verdicts().round(4).to_string(), flush=True)


def verdicts():
    """The rule in the docstring, from the select results."""
    r = pd.read_csv(SELECT_OUT)
    y = r[r.setup == "2024"].pivot(index="group", columns="seed", values="onset_pr_auc")
    held = r[r.setup == "held-out counties"].set_index("group").onset_pr_auc
    gain = y.div(y.loc[BASE], axis=1) - 1
    out = pd.DataFrame({"mean_gain_2024": gain.mean(axis=1), "seeds_better": (gain > 0).sum(axis=1),
                        "held_out_gain": held / held[BASE] - 1})
    out["kept"] = (out.seeds_better >= 4) & (out.held_out_gain > 0)
    return out.drop(index=BASE).reindex([*GROUPS, ALL])


def test():
    v = verdicts()
    print(v.round(4).to_string(), flush=True)
    kept = [g for g in GROUPS if v.loc[g, "kept"]]
    print("kept:", kept, flush=True)
    kept_inputs = list(dict.fromkeys(c for g in kept for c in GROUPS[g]))
    base = data.resolve_features(FEATURES) + WINDOW_V1   # E47 ran on the MO + IL recipe
    official = "warnings + outlook"
    versions = {official: models.NEEDS_COLUMNS["official"], BASE: base}
    if kept:
        versions["kept groups"] = base + [c for c in kept_inputs if c not in base]
    versions[ALL] = features_for(base, ALL)
    train = add_place(train_rows(TEST_TRAIN_YEARS))
    fitted = fit_versions({k: ("official" if k == official else "xgboost", f) for k, f in versions.items()},
                          train, official_counts()[0], seeds=(0, 1, 2, 3, 4), params=PARAMS)
    del train
    pred = predict_five_runs(fitted, add=add_place)
    seed_scores = {label: [score(pred.y, pred[f"{label}|seed{s}"])["pr_auc"] for s in range(1, 5)]
                   for label in versions if label != official}
    onsets = onset_hours(2025)
    first = storm_day(pd.Series([pd.Timestamp("2024-12-31")]))[0]
    row_day = ((storm_day(pred.block_start) - first).dt.days).to_numpy()
    onset_day = ((storm_day(onsets.hour) - first).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(max(row_day.max(), onset_day.max()) + 1))
    auc = {n: pr_auc_resamples(pred.y, pred[n], row_day, counts) for n in versions}
    rows = []
    for n in versions:
        p = pred[n].to_numpy()
        r = {"model": n, "onset_pr_auc": score(pred.y, p)["pr_auc"]}
        r["onset_pr_auc_lo"], r["onset_pr_auc_hi"] = interval(auc[n])
        for ref in (official, BASE):
            if n != ref:
                r[f"ratio_vs_{ref}"] = r["onset_pr_auc"] / score(pred.y, pred[ref])["pr_auc"]
                r[f"ratio_vs_{ref}_lo"], r[f"ratio_vs_{ref}_hi"] = interval(auc[n] / auc[ref])
                r[f"better_vs_{ref}"] = float(np.mean(auc[n] > auc[ref]))
        if n in seed_scores:
            r["seed_scores_1_4"] = " ".join(f"{s:.4f}" for s in seed_scores[n])
        flagged = pd.Series(p > np.quantile(p, 1 - EQUAL_SHARE), index=pred.index)
        hit = np.array(caught_flags(pred, flagged, onsets, LEAD), dtype=float)
        r["alert_share"], r["precision"] = flagged.mean(), pred.y[flagged].mean()
        r["caught"] = hit.mean()
        r["caught_lo"], r["caught_hi"] = interval(weighted_mean_resamples(hit, onset_day, counts))
        r["episodes"] = episodes(pred, flagged)
        rows.append(r)
        print({k: round(x, 4) if isinstance(x, float) else x for k, x in r.items()}, flush=True)
    pd.DataFrame(rows).to_csv(RESULTS / "place_extra_2025.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["select", "test"])
    {"select": select, "test": test}[parser.parse_args().stage]()
