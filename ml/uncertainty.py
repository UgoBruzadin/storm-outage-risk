"""Ranges for test-year scores: a paired bootstrap over storm days.

The hours of one storm rise and fall together, so resampling hours would give ranges far too
narrow. Instead whole storm days are resampled with replacement (SPC's convective day, 12 UTC to
12 UTC, so an evening storm isn't cut at midnight), and every model is scored on the same
resampled days. That gives a range for each score and for each difference between two models,
which is what "is it really better?" asks.

A resample is a weight per day (how many times it was drawn), applied to every row of that day,
so each score is computed once per resample without copying rows.
"""
import numpy as np
import pandas as pd

N_RESAMPLES = 1000


def storm_day(hours):
    """The convective day an hour belongs to: 12 UTC to 12 UTC, labelled by its first date."""
    return (pd.to_datetime(hours) - pd.Timedelta(hours=12)).dt.floor("D")


def day_weights(days, n=N_RESAMPLES, seed=0):
    """(n, n_days) draw counts, and each row's day index, for a bootstrap over days."""
    codes, uniques = pd.factorize(days)
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(len(uniques), np.full(len(uniques), 1 / len(uniques)), size=n)
    return counts, codes


def pr_auc_resamples_slow(y, p, codes, counts):
    """The direct version, one resample at a time (kept as the reference the test checks the fast one against)."""
    order = np.argsort(-np.asarray(p), kind="stable")
    y, p, codes = np.asarray(y, dtype=float)[order], np.asarray(p)[order], codes[order]
    last = np.r_[p[1:] != p[:-1], True]               # the last row of each run of tied scores
    out = np.empty(len(counts))
    for i, c in enumerate(counts):
        w = c[codes].astype(float)
        tp, fp = np.cumsum(w * y)[last], np.cumsum(w * (1 - y))[last]
        precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
        out[i] = np.sum(np.diff(np.r_[0, tp / tp[-1]]) * precision)
    return out


def pr_auc_resamples(y, p, codes, counts, block=50_000):
    """PR-AUC (sklearn's average_precision_score, weighted) for every resample, sorting once.

    Recall only moves at runs of tied scores that contain an outage (~0.5% of decisions), so only those runs count.
    At the end of each such run g, a resample's true positives are sum_d counts[d] x (outages of day d ranked at or
    above g) and its alerts sum_d counts[d] x (decisions of day d at or above g): two matrix products over the
    days for all resamples at once, instead of a weighted cumulative sum over every decision per resample. Every
    count is a whole number, so the result equals pr_auc_resamples_slow up to the order of the final sum, and is
    ~100x faster on the whole country's 27M decisions."""
    order = np.argsort(-np.asarray(p), kind="stable")
    y = np.asarray(y)[order].astype(bool)
    p, codes = np.asarray(p)[order], np.asarray(codes)[order]
    n_days = counts.shape[1]
    run_end = np.flatnonzero(np.r_[p[1:] != p[:-1], True])          # last row of each run of tied scores
    tp_run = np.cumsum(y)[run_end]
    ends = run_end[np.diff(np.r_[0, tp_run]) > 0]                    # runs where recall moves
    c = counts.T.astype(float)                                       # days x resamples
    by_day = np.argsort(codes, kind="stable")                        # row positions grouped by day, in rank order
    day_start = np.searchsorted(codes[by_day], np.arange(n_days + 1))
    pos_rows = np.flatnonzero(y)
    pos_by_day = pos_rows[np.argsort(codes[pos_rows], kind="stable")]
    pos_start = np.searchsorted(codes[pos_by_day], np.arange(n_days + 1))
    total_tp = np.bincount(codes[y], minlength=n_days) @ c           # each resample's outages
    ap = np.zeros(len(counts))
    prev_tp = np.zeros(len(counts))
    for lo in range(0, len(ends), block):                             # blocks of runs: bounded memory
        e = ends[lo:lo + block]
        n_rows = np.empty((len(e), n_days))
        n_pos = np.empty((len(e), n_days))
        for d in range(n_days):
            n_rows[:, d] = np.searchsorted(by_day[day_start[d]:day_start[d + 1]], e, side="right")
            n_pos[:, d] = np.searchsorted(pos_by_day[pos_start[d]:pos_start[d + 1]], e, side="right")
        tp, alerts = n_pos @ c, n_rows @ c                            # runs x resamples
        precision = np.divide(tp, alerts, out=np.zeros_like(tp), where=alerts > 0)
        d_tp = np.diff(np.vstack([prev_tp, tp]), axis=0)
        ap += (d_tp * precision).sum(axis=0)
        prev_tp = tp[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        return ap / total_tp


def weighted_mean_resamples(values, codes, counts):
    """The mean of `values` (e.g. 1 = caught, per outage) for every resample."""
    values = np.asarray(values, dtype=float)
    per_day_sum = np.bincount(codes, weights=values, minlength=counts.shape[1])
    per_day_n = np.bincount(codes, minlength=counts.shape[1])
    return (counts @ per_day_sum) / np.maximum(counts @ per_day_n, 1)


def interval(samples, level=0.95):
    lo, hi = np.quantile(samples, [(1 - level) / 2, (1 + level) / 2])
    return float(lo), float(hi)
