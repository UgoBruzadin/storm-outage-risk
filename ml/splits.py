"""How test rows are chosen. Each split yields (fold, train_index, test_index).

  time    train on some years, test on later ones: "can it predict the future?"
  county  k-fold by region: every region is tested by a model that never saw it
  random  k-fold by region-day hash — weathernext's approach. Neighbouring counties
          on the same storm day land on both sides, so it's optimistic on purpose.
"""
import hashlib

import numpy as np
from sklearn.model_selection import GroupKFold


def make_splits(df, kind, train_years=None, test_years=None, folds=5):
    if kind == "time":
        train_years = train_years or [int(df["year"].min())]
        test_years = test_years or [int(df["year"].max())]
        assert max(train_years) < min(test_years), "time split: train years must come before test years"
        yield 0, np.where(df["year"].isin(train_years))[0], np.where(df["year"].isin(test_years))[0]
    elif kind == "county":
        for fold, (tr, te) in enumerate(GroupKFold(n_splits=folds).split(df, groups=df["region_fips"])):
            yield fold, tr, te
    elif kind == "random":
        key = df["region_fips"] + df["block_start"].dt.date.astype(str)
        bucket = key.map(lambda k: int(hashlib.md5(k.encode()).hexdigest(), 16) % folds).to_numpy()
        for fold in range(folds):
            yield fold, np.where(bucket != fold)[0], np.where(bucket == fold)[0]
    else:
        raise ValueError(f"unknown split: {kind}")
