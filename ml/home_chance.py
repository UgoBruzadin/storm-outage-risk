"""The chance a typical home loses power: the expected share of a county's customers newly out (2025, 2 h ahead).

The headline model answers a county question: will at least 5% of customers be out? A household asks a different
one: will MY power go out? For a home picked at random in the county, that chance is the share of the county's
customers who lose power. EAGLE-I counts customers out per county, so this is measurable, unlike any finer number.

Target, for a decision at hour t about the 6 hours starting t + 2 (as the headline):
    newly out = (worst share out in the window - share out at t) / (share still on at t), clipped to 0..1
the chance that a home with power at t loses it in the window. It is a lower bound: customers who go out and come
back at different hours within the window are counted once at the worst hour.

Every decision hour is kept, during outages too (unlike the headline's new-outage rows). One XGBoost model with
the headline's features and window weather, fitted with cross-entropy on the share (objective reg:logistic), so
its output is an expected share; trained 2020-2024 on actual weather, scored on 2025 with the mean of the five
HRRR runs issued 2-6 hours before each decision. Against two baselines fitted on the same rows:
  usual        the county's average for the month (what a normal day looks like)
  warnings     the average under each combination of NWS warnings and SPC outlook
Scores: cross-entropy and squared error, as skill against `usual` (1 = perfect, 0 = no better than usual), with
storm-day ranges; and calibration: in bins of predicted chance, the share that actually lost power.

Usage: pixi run python -m ml.home_chance [--states MO]   (--states: a quick run on some states)
Writes ml/results/home_chance_2025.csv and home_chance_calibration_2025.csv.
"""
import argparse

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import (
    LEAD,
    TEST_YEAR,
    TRAIN_YEARS,
    WINDOW,
    add_actual_window,
    states_2025,
    window_from_forecast,
    with_version,
)
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT
from ml.place_extra import NAMES
from ml.uncertainty import day_weights, interval, storm_day, weighted_mean_resamples

RESULTS = data.ROOT / "ml" / "results"
OUT, CALIBRATION = RESULTS / "home_chance_2025.csv", RESULTS / "home_chance_calibration_2025.csv"
BINS = [0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1]
EPS = 1e-6


def newly_out(df):
    now = df.pct_out_now.clip(0, 100)
    return ((df.fut_max_pct - now) / (100 - now).clip(lower=EPS)).clip(0, 1)


def with_target(df):
    df = df[df.pct_out_now.notna()].copy()
    df["target"] = newly_out(df)
    return df


def load_train(states):
    """Training decisions, every hour (outages included), sampled like the headline's: every window reaching the
    5% line and data.NEG_FRAC of the others, weighted back. Unbiased for the share too, since a kept row stands
    for 1 / NEG_FRAC rows like it."""
    train = data.sampled_years(THRESHOLD_PCT, TRAIN_YEARS, LEAD, onsets_only=False, states=states,
                               add=lambda df, y: with_target(add_actual_window(df, y)))
    print(f"{len(train):,} training decisions standing for {train.weight.sum():,.0f}, "
          f"{train.region_fips.nunique()} counties", flush=True)
    return train


def test_states(states):
    """2025, every decision with all five runs, one state at a time."""
    keep = set(states) if states else None
    for s, _, shown in states_2025(lambda f: {n: window_from_forecast(f, k) for n, k in
                                              zip(NAMES, RUN_AGES, strict=True)}, onsets=False, every=True):
        if keep is None or s in keep:
            yield with_target(shown)


def cross_entropy(y, p):
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", help="comma-separated state abbreviations, for a quick run")
    a = ap.parse_args()
    fips = {v: k for k, v in data.STATE_ABBR.items()}
    states = [fips[s] for s in a.states.split(",")] if a.states else None
    train = load_train(states)
    out, calibration = OUT, CALIBRATION
    if states:                                  # a quick run never overwrites the full one
        out, calibration = (p.with_name(p.stem + "_" + a.states.replace(",", "_") + ".csv") for p in (OUT, CALIBRATION))

    features = data.resolve_features(FEATURES) + WINDOW
    # the baselines are weighted means over the sampled rows: estimates of the full table's means
    usual = models.RateBaseline(by=("region_fips", "month")).fit(train, train.target, sample_weight=train.weight)
    official = models.RateBaseline(by=tuple(models.NEEDS_COLUMNS["official"])).fit(
        train, train.target, sample_weight=train.weight)
    model = XGBRegressor(objective="reg:logistic", n_jobs=8, random_state=0, device=models.XGB_DEVICE, **PARAMS)
    model.fit(train[features], train.target, sample_weight=train.weight)
    del train
    print("trained", flush=True)

    parts = []
    for test in test_states(states):
        parts.append(pd.DataFrame({
            "block_start": test.block_start.to_numpy(), "target": test.target.to_numpy(),
            "usual": usual.predict_proba(test)[:, 1], "warnings": official.predict_proba(test)[:, 1],
            "model": np.mean([model.predict(with_version(test, features, n)) for n in NAMES], axis=0)}))
        del test
    test = pd.concat(parts, ignore_index=True)
    print(f"{TEST_YEAR} decisions with all five runs: {len(test):,}", flush=True)
    pred = {k: test[k].to_numpy() for k in ("usual", "warnings", "model")}

    y = test.target.to_numpy()
    first = storm_day(pd.Series([pd.Timestamp(f"{TEST_YEAR - 1}-12-31")]))[0]
    days = (storm_day(test.block_start) - first).dt.days.to_numpy()
    counts, codes = day_weights(days)
    loss = {k: {"cross_entropy": cross_entropy(y, p), "squared": (y - p) ** 2} for k, p in pred.items()}
    rows = []
    for k, p in pred.items():
        r = {"forecast": k, "decisions": len(y), "mean_chance": float(p.mean()), "mean_newly_out": float(y.mean())}
        for m in ("cross_entropy", "squared"):
            r[m] = float(loss[k][m].mean())
            if k != "usual":
                ours = weighted_mean_resamples(loss[k][m], codes, counts)
                base = weighted_mean_resamples(loss["usual"][m], codes, counts)
                r[f"{m}_skill"] = 1 - r[m] / float(loss["usual"][m].mean())
                r[f"{m}_skill_lo"], r[f"{m}_skill_hi"] = interval(1 - ours / base)
        rows.append(r)
        print({k2: round(v, 5) if isinstance(v, float) else v for k2, v in r.items()}, flush=True)
    pd.DataFrame(rows).to_csv(out, index=False)

    cal = []
    for k, p in pred.items():
        b = pd.cut(p, BINS, include_lowest=True)
        g = pd.DataFrame({"bin": b, "p": p, "y": y}).groupby("bin", observed=True)
        cal.append(g.agg(decisions=("y", "size"), predicted=("p", "mean"), actual=("y", "mean"),
                         any_out=("y", lambda v: (v > 0).mean())).reset_index().assign(forecast=k))
    cal = pd.concat(cal)
    cal["bin"] = cal.bin.astype(str)
    cal.to_csv(calibration, index=False)
    print(cal.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
