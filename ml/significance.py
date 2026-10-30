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
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import average_precision_score

from ml import data
from ml.export_hourly import MODELS, TEST_YEAR, predictions
from ml.uncertainty import day_weights, pr_auc_resamples, storm_day

N_PERMUTATIONS = 1000
COMPARISONS = [  # (challenger, reference)
    ("No forecasts", "Warnings + outlook"),
    ("With HRRR forecasts (mean of 5 runs)", "Warnings + outlook"),
    ("With HRRR forecasts (mean of 5 runs)", "No forecasts"),
    ("With HRRR forecasts (mean of 5 runs)", "With HRRR forecasts (newest run)"),
    ("Perfect weather (ceiling)", "With HRRR forecasts (mean of 5 runs)"),
]


def main():
    pred = predictions()
    y = pred.y.to_numpy()
    first = pd.Timestamp(f"{TEST_YEAR - 1}-12-31")
    day = (storm_day(pred.block_start) - first).dt.days.to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    boot = {}
    rows = []
    rng = np.random.default_rng(0)
    for a, b in COMPARISONS:
        for m in (a, b):
            if m not in boot:
                boot[m] = pr_auc_resamples(y, pred[MODELS[m]], day, counts)
        pa, pb = rankdata(pred[MODELS[a]]) / len(pred), rankdata(pred[MODELS[b]]) / len(pred)
        observed = average_precision_score(y, pa) - average_precision_score(y, pb)
        null = np.empty(N_PERMUTATIONS)
        for i in range(N_PERMUTATIONS):
            swap = rng.random(day.max() + 1)[day] < 0.5
            null[i] = (average_precision_score(y, np.where(swap, pb, pa))
                       - average_precision_score(y, np.where(swap, pa, pb)))
        diff = boot[a] - boot[b]
        rows.append({"challenger": a, "reference": b, "pr_auc_challenger": average_precision_score(y, pred[MODELS[a]]),
                     "pr_auc_reference": average_precision_score(y, pred[MODELS[b]]),
                     "share_of_resamples_better": float((diff > 0).mean()),
                     "p_bootstrap": float(max((diff <= 0).mean(), 1 / len(diff))),
                     "p_permutation": float(((null >= observed).sum() + 1) / (N_PERMUTATIONS + 1)),
                     "n_storm_days": int(day.max() + 1)})
        print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / "significance_2025.csv", index=False)


if __name__ == "__main__":
    main()
