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


def pr_auc_resamples(y, p, codes, counts):
    """PR-AUC (sklearn's average_precision_score, weighted) for every resample, sorting once."""
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


def weighted_mean_resamples(values, codes, counts):
    """The mean of `values` (e.g. 1 = caught, per outage) for every resample."""
    values = np.asarray(values, dtype=float)
    per_day_sum = np.bincount(codes, weights=values, minlength=counts.shape[1])
    per_day_n = np.bincount(codes, minlength=counts.shape[1])
    return (counts @ per_day_sum) / np.maximum(counts @ per_day_n, 1)


def interval(samples, level=0.95):
    lo, hi = np.quantile(samples, [(1 - level) / 2, (1 + level) / 2])
    return float(lo), float(hi)
