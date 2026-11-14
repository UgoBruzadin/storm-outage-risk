"""Is one model really better than another on 2025? Paired tests over storm days (docs/experiments.md, E23).

Two models' individual 95% ranges can overlap even when one is better on nearly every resample, because both
rise and fall with the same storms. The question is about the difference, so both tests are paired:

  bootstrap    resample 2025's storm days 1,000 times (ml/uncertainty.py), score both models on each
               resample; p = share of resamples where the challenger is not better (one-sided)
  permutation  the null "the two models are equally good": on each storm day, swap the two models'
               predictions with probability 1/2, and recompute the difference 1,000 times; p = share of
               swapped differences at least as large as the real one. Scores are turned into percentile
               ranks within each model first, so swapping doesn't mix two probability scales

Usage: pixi run python -m ml.significance
Writes ml/results/significance_2025.csv. Reads the predictions saved by ml/export_hourly.py's sources.
"""
import os

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import rankdata
from sklearn.metrics import average_precision_score

from ml import data
from ml.export_hourly import MODELS, TEST_YEAR, predictions
from ml.uncertainty import day_weights, pr_auc_resamples, storm_day

N_PERMUTATIONS = 1000
# permutations run in parallel (each is a PR-AUC over every 2025 decision: ~3 h per comparison on one core for the
# whole country); the swaps are drawn in the same order as one core would, so the p-values are the same
N_JOBS = min(12, os.cpu_count() or 1)


def _swapped_differences(y, pa, pb, day, swaps):
    """The permutation null for a batch of per-day swap draws (uniform numbers, one per storm day)."""
    out = np.empty(len(swaps))
    for i, u in enumerate(swaps):
        swap = u[day] < 0.5
        out[i] = average_precision_score(y, np.where(swap, pb, pa)) - average_precision_score(y, np.where(swap, pa, pb))
    return out
COMPARISONS = [  # (challenger, reference)
    ("No forecasts", "Warnings + outlook"),
    ("With HRRR forecasts (mean of 5 runs)", "Warnings + outlook"),
    ("With HRRR forecasts (mean of 5 runs)", "No forecasts"),
    ("With HRRR forecasts (mean of 5 runs)", "With HRRR forecasts (newest run)"),
    ("Perfect weather (ceiling)", "With HRRR forecasts (mean of 5 runs)"),
]


OUT = data.ROOT / "ml" / "results" / "significance_2025.csv"
# comparisons finished so far (a comparison is ~45 min for the whole country): a stopped run resumes after the
# last one, and OUT is written only when every comparison is done, so the pipeline never takes a partial file
# for a finished step
PARTIAL = OUT.with_suffix(".partial.csv")


def main():
    pred = predictions()
    y = pred.y.to_numpy()
    first = pd.Timestamp(f"{TEST_YEAR - 1}-12-31")
    day = (storm_day(pred.block_start) - first).dt.days.to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    boot = {}
    rows = pd.read_csv(PARTIAL).to_dict("records") if PARTIAL.exists() else []
    assert [(r["challenger"], r["reference"]) for r in rows] == COMPARISONS[:len(rows)], f"{PARTIAL} is stale"
    if rows:
        print(f"resuming after {len(rows)} comparisons saved in {PARTIAL}", flush=True)
    rng = np.random.default_rng(0)
    for i, (a, b) in enumerate(COMPARISONS):
        # drawn for every comparison, done or not, so a resumed run uses the same swaps as an uninterrupted one
        draws = [rng.random(day.max() + 1) for _ in range(N_PERMUTATIONS)]
        if i < len(rows):
            continue
        for m in (a, b):
            if m not in boot:
                boot[m] = pr_auc_resamples(y, pred[MODELS[m]], day, counts)
        pa, pb = rankdata(pred[MODELS[a]]) / len(pred), rankdata(pred[MODELS[b]]) / len(pred)
        observed = average_precision_score(y, pa) - average_precision_score(y, pb)
        batches = np.array_split(np.arange(N_PERMUTATIONS), N_JOBS * 4)
        null = np.concatenate(Parallel(n_jobs=N_JOBS)(
            delayed(_swapped_differences)(y, pa, pb, day, [draws[i] for i in b]) for b in batches))
        diff = boot[a] - boot[b]
        rows.append({"challenger": a, "reference": b, "pr_auc_challenger": average_precision_score(y, pred[MODELS[a]]),
                     "pr_auc_reference": average_precision_score(y, pred[MODELS[b]]),
                     "share_of_resamples_better": float((diff > 0).mean()),
                     "p_bootstrap": float(max((diff <= 0).mean(), 1 / len(diff))),
                     "p_permutation": float(((null >= observed).sum() + 1) / (N_PERMUTATIONS + 1)),
                     "n_storm_days": int(day.max() + 1)})
        print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(PARTIAL, index=False)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    PARTIAL.unlink()


if __name__ == "__main__":
    main()
