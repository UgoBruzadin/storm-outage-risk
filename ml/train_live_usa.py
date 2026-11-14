"""Train the frozen model for the USA live forecast (the E55 recipe, without live outage data).

The recipe E55 chose on 2024 (docs/experiments.md, E55: XGBoost depth 8, minimum child weight 100, 1,600 trees; the
headline inputs plus duration / spread, roads + street canopy, history, location and the E47 place groups), minus the
four outage inputs a live job can't get (live/features.OUTAGE_INPUTS, as E43 and ml/train_live.py). Trained on
actual weather (sampled as E54), fresh new outages, 2 hours ahead; fed the mean of the five HRRR runs issued 2-6 hours
before each decision when it predicts.

Two models, both seed 0:
  final     trained on 2020-2025: the model the live job ships
  held out  the same recipe trained on 2020-2024 and scored on every 2025 decision with the five-run mean: its
            score against warnings + outlook (the live USA counterpart of E43), and the alert level at the top
            0.75% of 2025 county-hours, chosen without 2025 outcomes in training (ml/train_live.py's choice)
The final model's own top 0.75% of 2025 (in sample) is saved beside it.

Never writes live/model (the frozen MO + IL blind test).

Usage: pixi run -e gpu python -m ml.train_live_usa [--smoke]
Writes live/model_usa/model.json + meta.json, and ml/results/live_usa_2025.csv (held-out score);
2025 chances in data/cache/live_usa/pred_2025.parquet.
"""
import argparse
import json
import time
from datetime import UTC, datetime

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap

from live.features import OUTAGE_INPUTS
from ml import data, models
from ml import forecast_test as ft
from ml import usa_ablation as ua
from ml import usa_final_test as uf
from ml.moving_window import THRESHOLD_PCT
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

YEARS, TEST_YEAR, SHARE = [2020, 2021, 2022, 2023, 2024, 2025], 2025, ft.EQUAL_SHARE
OUT = data.ROOT / "live" / "model_usa"
CACHE = data.ROOT / "data" / "cache" / "live_usa"
RESULT = data.ROOT / "ml" / "results" / "live_usa_2025.csv"


def train_rows(years, states=None):
    df = data.sampled_years(THRESHOLD_PCT, years, ft.LEAD, add=ua.add_train, **({"states": states} if states else {}))
    return df[df.win_gust_max_ms.notna()].reset_index(drop=True)


def score(fitted, features, smoke):
    """Every 2025 decision with all five runs, a state at a time: each model's mean over the runs."""
    window = [c for c in features if c in ua.WINDOW + ua.DURATION]
    states = data.warehouse_states()[:2] if smoke else data.warehouse_states()
    parts = []
    for rows, runs in uf.scored_states(states):
        out = rows[["region_fips", "block_start", "y"]].copy()
        for name, m in fitted.items():
            per_run = []
            for r in runs:
                x = rows[[c for c in features if c not in window]].copy()
                x[window] = r[window].to_numpy()
                per_run.append(m.predict_proba(x[features])[:, 1])
            out[name] = np.mean(per_run, axis=0).astype("float32")
        parts.append(out)
        del rows, runs
    return pd.concat(parts, ignore_index=True)


def report(pred):
    """Held-out 2025 scores: the live model, the E55 model with outage data (usa_final_test), the current headline,
    warnings + outlook; ratios with storm-day ranges, and alerts at the shared alert share."""
    con = duckdb.connect()
    old = con.sql(f"SELECT region_fips, block_start, p_official, p_mean FROM '{uf.DECISIONS}'").df()
    e55 = uf.OUT_DIR / "pred_2025.parquet"
    if e55.exists():
        old = old.merge(con.sql(f"SELECT region_fips, block_start, seed0 AS p_e55 FROM '{e55}'").df(),
                        on=["region_fips", "block_start"], how="left")
    con.close()
    old["region_fips"] = old.region_fips.astype(str)
    pred = pred.merge(old, on=["region_fips", "block_start"], how="inner")
    p = {"warnings + outlook": pred.p_official, "current headline (with outage data)": pred.p_mean}
    if "p_e55" in pred and pred.p_e55.notna().all():
        p["E55 model (with outage data)"] = pred.p_e55
    p["live USA model (held out)"] = pred.held_out
    p = {k: v.to_numpy() for k, v in p.items()}
    y = pred.y.to_numpy().astype(int)
    day = ((storm_day(pred.block_start) - storm_day(pred.block_start).min()).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    boot = {k: pr_auc_resamples(y, v, day, counts) for k, v in p.items()}
    n, P, live = len(y), y.sum(), "live USA model (held out)"
    rows = []
    for k, v in p.items():
        r = {"model": k, "onset_pr_auc": ap(y, v)}
        r["onset_pr_auc_lo"], r["onset_pr_auc_hi"] = interval(boot[k])
        if k != "warnings + outlook":
            r["ratio_vs_official"] = r["onset_pr_auc"] / ap(y, p["warnings + outlook"])
            r["ratio_vs_official_lo"], r["ratio_vs_official_hi"] = interval(boot[k] / boot["warnings + outlook"])
        if k != live:
            r["live_vs_this"] = ap(y, p[live]) / r["onset_pr_auc"]
            r["live_vs_this_lo"], r["live_vs_this_hi"] = interval(boot[live] / boot[k])
        top = np.argpartition(-v, int(SHARE * n))[:int(SHARE * n)]
        tp = y[top].sum()
        r["precision_at_share"], r["recall_at_share"], r["f1_at_share"] = tp / len(top), tp / P, 2 * tp / (len(top) + P)
        r["n_decisions"], r["n_outages"] = n, int(P)
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="2 states, 5 trees, trained on 2024 (+2025); scratch dirs")
    args = parser.parse_args()
    global OUT, CACHE, RESULT
    if args.smoke:
        OUT, CACHE = OUT.with_name("model_usa_smoke"), CACHE.with_name("live_usa_smoke")
        RESULT = CACHE / RESULT.name
        ua.SMOKE = True
    assert OUT.name != "model", "never write live/model"
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    size, kept, e55_features, params = uf.recipe()
    features = [c for c in e55_features if c not in OUTAGE_INPUTS]
    dropped = [c for c in e55_features if c in OUTAGE_INPUTS]
    assert len(dropped) == len(OUTAGE_INPUTS), f"expected all four outage inputs in E55's list, found {dropped}"
    if args.smoke:
        params = params | {"n_estimators": 5}
    print(f"recipe: {size}; groups {kept}; {len(features)} inputs (dropped {dropped})", flush=True)

    years = [2024, 2025] if args.smoke else YEARS
    states = data.warehouse_states()[:2] if args.smoke else None
    paths = {"final": OUT / "model.json", "held_out": CACHE / "held_out_2020_2024.json"}
    fitted = {}
    train = None
    for name, path in paths.items():
        m = models.build("xgboost", params | {"random_state": 0})
        if path.exists():
            m.load_model(path)
        else:
            if train is None:
                train = train_rows(years, states)
                print(f"training rows: {len(train):,}, {int(train.y.sum()):,} new outages ({time.time() - t0:.0f}s)",
                      flush=True)
            t = train if name == "final" else train[train.block_start.dt.year < TEST_YEAR]
            m.fit(t[features], t.y, sample_weight=t.weight)
            m.save_model(path)
            if name == "final":
                stats = {"training_rows": len(t), "training_positives": int(t.y.sum()),
                         "training_rows_stand_for": float(t.weight.sum())}
                (CACHE / "final_stats.json").write_text(json.dumps(stats))
        fitted[name] = m
        print(f"fitted {name} ({time.time() - t0:.0f}s)", flush=True)
    del train

    pred = score(fitted, features, args.smoke)
    pred.to_parquet(CACHE / "pred_2025.parquet", index=False)
    print(f"{TEST_YEAR}: {len(pred):,} decisions scored, {int(pred.y.sum()):,} new outages ({time.time() - t0:.0f}s)",
          flush=True)
    out = report(pred)
    out.to_csv(RESULT, index=False)

    meta = {
        "trained": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "recipe": "docs/experiments.md E55, without the four outage inputs (E43)",
        "size": size, "input_groups": kept, "train_years": years, "lead_hours": ft.LEAD,
        "threshold_pct": THRESHOLD_PCT, "run_ages": ft.RUN_AGES, "params": params, "features": features,
        "dropped_outage_inputs": dropped, "states": len(data.warehouse_states()),
        **json.loads((CACHE / "final_stats.json").read_text()),
        "alert_share": SHARE,
        "alert_level_held_out": float(np.quantile(pred.held_out, 1 - SHARE)),
        "alert_level_in_sample": float(np.quantile(pred.final, 1 - SHARE)),
        "held_out_2025": out.set_index("model").onset_pr_auc.round(4).to_dict(),
    }
    meta["alert_level"] = meta["alert_level_held_out"]
    meta["alert_level_choice"] = "held out: the same recipe trained on 2020-2024, its top 0.75% of 2025 hours"
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    show = [c for c in ["model", "onset_pr_auc", "onset_pr_auc_lo", "onset_pr_auc_hi", "ratio_vs_official",
                        "live_vs_this", "live_vs_this_lo", "live_vs_this_hi", "precision_at_share",
                        "recall_at_share", "f1_at_share"] if c in out]
    print(out[show].round(4).to_string(index=False))
    print({k: meta[k] for k in ("alert_level", "alert_level_in_sample", "training_rows", "training_positives")})
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
