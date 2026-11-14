"""The E55 model on 2025, once (docs/experiments.md, E55, "After E55").

E55 chose, on 2024 only: XGBoost depth 8, minimum child weight 100, 1,600 trees, and the headline inputs plus five
groups (duration / spread of wind, roads + street canopy, history, location, the E47 place groups). Here that model is
trained on 2020-2024 (actual weather, sampled as E54; seeds 0-2) and scored on every 2025 decision with the mean over
the five HRRR runs issued 2-6 hours before it, exactly as the headline. It is compared on the same decisions with the
current headline (its saved 2025 chances, data/explore/decisions_2025.parquet) and warnings + outlook.

Reported: onset PR-AUC with 95% storm-day ranges, paired ratios (and the share of resamples where the new model is
better), and alerts at one shared alert share (the riskiest 0.75% of county-hours: precision, recall, F1), plus each
model's best F1. "new model" is seed 0, the recipe as it would ship; "new model, 3 seeds" averages the three.

Usage: pixi run -e gpu python -m ml.usa_final_test [--smoke]
Writes ml/results/usa_final_2025.csv; models in data/cache/usa_final/, 2025 chances in
data/cache/usa_final/pred_2025.parquet.
"""
import argparse
import time

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap

from ml import data, models
from ml import forecast_test as ft
from ml import usa_ablation as ua
from ml.moving_window import THRESHOLD_PCT
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

TEST_YEAR, AGES, SEEDS, SHARE = 2025, ft.RUN_AGES, range(3), 0.0075
OUT_DIR = data.ROOT / "data" / "cache" / "usa_final"
RESULT = data.ROOT / "ml" / "results" / "usa_final_2025.csv"
DECISIONS = data.ROOT / "data" / "explore" / "decisions_2025.parquet"


def recipe():
    """E55's choice, read from its verdicts: the size stage's setting and the input groups kept."""
    v = pd.read_csv(ua.RESULTS / ua.VERDICTS.name)
    size = v[(v.stage == "size") & v.kept].sort_values("pr_auc").arm.iloc[-1]
    kept = v[(v.stage == "inputs") & v.kept].arm.tolist()
    together = v[(v.stage == "combine") & (v.arm == "kept together")]
    assert len(together) and together.kept.iloc[0], "E55's combine stage didn't keep the groups together"
    features = ua.BASE + list(dict.fromkeys(c for g in kept for c in ua.GROUPS[g] if c not in ua.BASE))
    params = ua.PARAMS | ua.SIZES[size] | ({"monotone_constraints": {c: 1 for c in ua.MONOTONE}}
                                           if "monotone gust" in kept else {})
    return size, kept, features, params


def scored_states(states):
    """2025 a state at a time: the decisions with all five runs, and each run's window inputs (headline + duration)."""
    for s in states:
        f = ft.forecasts(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31", states=[s])
        if f.empty:
            continue
        rows = data.load_hourly(THRESHOLD_PCT, [TEST_YEAR], LEAD, states=[s], float32=True)
        rows["region_fips"] = rows.region_fips.astype(str)
        runs = []
        for age in AGES:
            w = ft.window_from_forecast(f, age).merge(ua.duration_forecast(f, age), on=["region_fips", "block_start"])
            runs.append(rows[["region_fips", "block_start"]].merge(w, on=["region_fips", "block_start"], how="left"))
        del f
        have = np.logical_and.reduce([r.win_gust_max_ms.notna().to_numpy() for r in runs])
        rows, runs = rows[have].reset_index(drop=True), [r[have].reset_index(drop=True) for r in runs]
        rows["win_gust_max_ms"] = runs[0].win_gust_max_ms.to_numpy()    # add_inputs bins the gust; replaced per run
        rows = ua.add_inputs(rows)
        print(f"{data.STATE_ABBR.get(s, s)}: {len(rows):,} decisions of {TEST_YEAR} with all five runs", flush=True)
        yield rows, runs


LEAD = ua.LEAD


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="2 states, 5 trees, one seed, trained on 2024 only")
    args = parser.parse_args()
    global OUT_DIR, RESULT
    if args.smoke:
        OUT_DIR, RESULT = OUT_DIR.with_name("usa_final_smoke"), OUT_DIR.with_name("usa_final_smoke") / RESULT.name
        ua.SMOKE = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    size, kept, features, params = recipe()
    seeds = [0] if args.smoke else list(SEEDS)
    if args.smoke:
        params = params | {"n_estimators": 5}
    print(f"recipe: {size}; groups {kept}; {len(features)} inputs", flush=True)

    ua.TRAIN_YEARS = [2024] if args.smoke else [2020, 2021, 2022, 2023, 2024]
    fitted = {}
    for s in seeds:
        path = OUT_DIR / f"model_seed{s}.json"
        m = models.build("xgboost", params | {"random_state": s})
        if path.exists():
            m.load_model(path)
        else:
            if "train" not in locals():
                train = ua.train_rows()
                print(f"training rows: {len(train):,}, {int(train.y.sum()):,} new outages "
                      f"({time.time() - t0:.0f}s)", flush=True)
            m.fit(train[features], train.y, sample_weight=train.weight)
            m.save_model(path)
        fitted[s] = m
        print(f"fitted seed {s} ({time.time() - t0:.0f}s)", flush=True)
    if "train" in locals():
        del train

    window = [c for c in features if c in ft.WINDOW + ua.DURATION]
    states = data.warehouse_states()[:2] if args.smoke else data.warehouse_states()
    parts = []
    for rows, runs in scored_states(states):
        out = rows[["region_fips", "block_start", "y"]].copy()
        for s, m in fitted.items():
            per_run = []
            for r in runs:
                x = rows[[c for c in features if c not in window]].copy()
                x[window] = r[window].to_numpy()
                per_run.append(m.predict_proba(x[features])[:, 1])
            out[f"seed{s}"] = np.mean(per_run, axis=0).astype("float32")
        parts.append(out)
        del rows, runs
    pred = pd.concat(parts, ignore_index=True)

    con = duckdb.connect()
    old = con.sql(f"SELECT region_fips, block_start, p_official, p_mean FROM '{DECISIONS}'").df()
    con.close()
    old["region_fips"] = old.region_fips.astype(str)
    n_new = len(pred)
    pred = pred.merge(old, on=["region_fips", "block_start"], how="inner")
    pred.to_parquet(OUT_DIR / "pred_2025.parquet", index=False)
    print(f"2025: {n_new:,} decisions scored, {len(pred):,} shared with the saved headline, "
          f"{int(pred.y.sum()):,} new outages ({time.time() - t0:.0f}s)", flush=True)

    p = {"warnings + outlook": pred.p_official.to_numpy(), "current headline": pred.p_mean.to_numpy(),
         "new model": pred.seed0.to_numpy()}
    if len(seeds) > 1:
        p["new model, 3 seeds"] = pred[[f"seed{s}" for s in seeds]].mean(axis=1).to_numpy()
    y = pred.y.to_numpy().astype(int)
    day = ((storm_day(pred.block_start) - storm_day(pred.block_start).min()).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    boot = {k: pr_auc_resamples(y, v, day, counts) for k, v in p.items()}
    n, P = len(y), y.sum()
    rows = []
    for k, v in p.items():
        r = {"model": k, "onset_pr_auc": ap(y, v)}
        r["onset_pr_auc_lo"], r["onset_pr_auc_hi"] = interval(boot[k])
        for ref in ("warnings + outlook", "current headline"):
            if k != ref:
                r[f"ratio_vs_{ref}"] = r["onset_pr_auc"] / ap(y, p[ref])
                r[f"ratio_vs_{ref}_lo"], r[f"ratio_vs_{ref}_hi"] = interval(boot[k] / boot[ref])
                r[f"better_than_{ref}"] = float(np.mean(boot[k] > boot[ref]))
        top = np.argpartition(-v, int(SHARE * n))[:int(SHARE * n)]
        tp = y[top].sum()
        r["precision_at_share"], r["recall_at_share"] = tp / len(top), tp / P
        r["f1_at_share"] = 2 * tp / (len(top) + P)
        o = np.argsort(-v, kind="stable")
        cum = np.cumsum(y[o])
        f1 = 2 * cum / (np.arange(1, n + 1) + P)
        r["best_f1"], r["best_f1_share"] = float(f1.max()), float((f1.argmax() + 1) / n)
        r["n_decisions"], r["n_outages"] = n, int(P)
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(RESULT, index=False)
    show = ["model", "onset_pr_auc", "onset_pr_auc_lo", "onset_pr_auc_hi", "ratio_vs_warnings + outlook",
            "ratio_vs_current headline", "ratio_vs_current headline_lo", "ratio_vs_current headline_hi",
            "better_than_current headline", "precision_at_share", "recall_at_share", "f1_at_share", "best_f1"]
    print(out[show].round(4).to_string(index=False))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
