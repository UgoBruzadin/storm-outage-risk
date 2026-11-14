"""More wind inputs: county-wide, duration and spread, radar and lightning (Missouri + Illinois, docs/experiments.md).

The USA test found official warnings beat the model in the strongest gusts (window gust >= 35 m/s: 0.74x). The
headline model already uses each window's *maximum* gust, but at one grid cell per county (the one nearest its
centre point) and with no sense of how long the wind lasts. Each arm adds one family of inputs to the headline
recipe (FEATURES + window weather, XGBoost, 2 hours ahead, fresh new outages):

  headline              as now
  + county-wide wind    the window's strongest gust and hourly wind anywhere in the county, and the largest share
                        of the county with gusts >= 20 m/s / wind >= 18 m/s
  + duration / spread   at the point: hours with gusts >= 15 and >= 20 m/s, mean and median gust, the largest
                        gust minus mean wind (gustiness)
  + radar + lightning   county-wide: strongest simulated radar, share >= 45 dBZ, storm-column ice (VIL), lightning
                        (max, share of cells with any)
  + all of the above

Training (2020-2024) uses the weather that actually happened: Open-Meteo for the point (as the headline), and for
county-wide values the HRRR run issued 1 hour before each hour (forecast hour 1, ingest/fetch_hrrr_forecast_area.py:
for the point it matches Open-Meteo to rounding). 2025 is scored with the mean over the five runs issued 2-6 hours
before each decision, every window input taken from the run, as the headline. Missouri + Illinois only: the
county-wide archive (data/raw/weather/hrrr_fcst_area) is complete for those 216 counties.

Three seeds per arm. The difference against the headline gets a 95% range from a storm-day bootstrap of the
seed-averaged chances. Scores are also split by the window's actual strongest gust, at the point and county-wide.

Usage: pixi run python -m ml.wind_inputs [--seeds 3] [--jobs 8]
Writes ml/results/wind_inputs_2025.csv and wind_inputs_by_gust_2025.csv.
"""
import argparse
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score as ap

from ml import data, models
from ml import forecast_test as ft

# a record of an experiment on the Missouri + Illinois recipe: pinned to it (moving_window.FEATURES_V1)
from ml.moving_window import FEATURES_V1 as FEATURES
from ml.moving_window import PARAMS_V1 as PARAMS
from ml.moving_window import THRESHOLD_PCT
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

STATES = ["17", "29"]                        # Illinois, Missouri
AREA_DIR = data.ROOT / "data" / "raw" / "weather" / "hrrr_fcst_area"
RESULTS = data.ROOT / "ml" / "results"
MODELS = data.ROOT / "data" / "cache" / "wind_inputs_models"       # delete to refit (after changing inputs)
TRAIN_YEARS, TEST_YEAR, LEAD, AGES = [2020, 2021, 2022, 2023, 2024], 2025, ft.LEAD, ft.RUN_AGES

AREA_WIND = ["win_area_gust_max", "win_area_gust_share20", "win_area_wind1h_max", "win_area_wind1h_share18"]
DURATION = ["win_gust_hours15", "win_gust_hours20", "win_gust_mean", "win_gust_median", "win_gustiness_max"]
RADAR = ["win_area_refc_max", "win_area_refc_share45", "win_area_vil_max", "win_area_ltng_max", "win_area_ltng_share"]
NEW = AREA_WIND + DURATION + RADAR
WINDOW = ft.WINDOW_V1 + NEW                     # every window input, swapped per run when scoring
ARMS = {"headline": [], "+ county-wide wind": AREA_WIND, "+ duration / spread": DURATION,
        "+ radar + lightning": RADAR, "+ all of the above": NEW}
GUST_BINS = [0, 15, 25, 35, np.inf]


def hourly_inputs(h):
    """Per-hour columns the new window inputs summarize."""
    h = h.copy()
    h["g15"] = (h.gust_ms >= 15).astype("float32").where(h.gust_ms.notna())
    h["g20"] = (h.gust_ms >= 20).astype("float32").where(h.gust_ms.notna())
    h["gustiness"] = h.gust_ms - h.wind10_ms
    return h


def summarize_new(g):
    """The new 6-hour inputs from an aggregator over a window's hours (rolling or groupby)."""
    return pd.DataFrame({
        "win_gust_hours15": g["g15"].sum(), "win_gust_hours20": g["g20"].sum(),
        "win_gust_mean": g["gust_ms"].mean(), "win_gust_median": g["gust_ms"].median(),
        "win_gustiness_max": g["gustiness"].max(),
        **{f"win_{c}": g[c].max() for c in [a.removeprefix("win_") for a in AREA_WIND + RADAR]},
    })


NEW_HOURLY = ["gust_ms", "g15", "g20", "gustiness"] + [a.removeprefix("win_") for a in AREA_WIND + RADAR]


def area_f01(years):
    """County-wide values each hour, from the run issued 1 hour before (forecast hour 1): the 'actual' county-wide
    weather. Covers the first of `years` through the first days of the year after the last."""
    cols = ["hour", "region_fips"] + [a.removeprefix("win_") for a in AREA_WIND + RADAR]
    days = pd.date_range(f"{min(years)}-01-01", f"{max(years) + 1}-01-02", freq="D")
    parts = [pq.read_table(p, columns=cols, filters=[("fhour", "=", 1)]).to_pandas()
             for p in (AREA_DIR / f"{d:%Y%m%d}.parquet" for d in days) if p.exists()]
    return pd.concat(parts, ignore_index=True)


def actual_windows(years):
    """For each decision hour: the headline's window inputs (Open-Meteo) and the new ones, from the weather that
    actually happened over hours h + LEAD ... h + LEAD + 5."""
    hw = ft.actual_hourly(years, states=STATES, until=f"{max(years) + 1}-01-02")
    head = ft.window_from_hourly(hw)[["block_start", "region_fips", *ft.WINDOW_V1]]   # its own duration below
    hw = hourly_inputs(hw).merge(area_f01(years), on=["region_fips", "hour"], how="left")
    parts = []
    for fips, r in hw.groupby("region_fips"):
        r = r.set_index("hour").sort_index()
        r = r.reindex(pd.date_range(r.index.min(), r.index.max(), freq="h"))
        s = summarize_new(r[NEW_HOURLY].rolling(6, min_periods=6))
        s.index = s.index - pd.Timedelta(hours=LEAD + 5)
        parts.append(s.assign(region_fips=fips))
    new = pd.concat(parts).rename_axis("block_start").reset_index()
    return head.merge(new, on=["region_fips", "block_start"], how="left")


def run_windows(f, age):
    """For each decision hour h: every window input from the run issued `age` hours before h."""
    first = age + LEAD
    g = f[f.fhour.between(first, first + 5)]
    head = ft.window_from_forecast(g, age)[["region_fips", "block_start", *ft.WINDOW_V1]]
    new = summarize_new(hourly_inputs(g)[["region_fips", "run", *NEW_HOURLY]].groupby(["region_fips", "run"]))
    new = new.reset_index()
    new["block_start"] = new.pop("run") + pd.Timedelta(hours=age)
    return head.merge(new, on=["region_fips", "block_start"], how="left")


def test_forecasts():
    days = pd.date_range(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31", freq="D")
    f = pd.concat([pd.read_parquet(AREA_DIR / f"{d:%Y%m%d}.parquet") for d in days
                   if (AREA_DIR / f"{d:%Y%m%d}.parquet").exists()], ignore_index=True)
    f["wind10_ms"] = np.hypot(f.u10, f.v10)
    f["wind850_ms"] = np.hypot(f.u850, f.v850)
    return f


def rows(years):
    df = data.load_hourly(THRESHOLD_PCT, years, LEAD, states=STATES, float32=True)
    df["region_fips"] = df.region_fips.astype(str)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=8, help="CPU threads per fit")
    args = parser.parse_args()
    t0 = time.time()
    base = [c for c in data.resolve_features(FEATURES) if c not in ft.WINDOW_V1]
    official = models.NEEDS_COLUMNS["official"]

    train = rows(TRAIN_YEARS).merge(actual_windows(TRAIN_YEARS), on=["region_fips", "block_start"], how="inner")
    train = train.dropna(subset=["win_gust_max_ms"]).reset_index(drop=True)
    train = train.astype({c: "float32" for c in base + WINDOW if train[c].dtype != "float32"})
    print(f"train: {len(train):,} decisions, {int(train.y.sum()):,} new outages, "
          f"county-wide known {train.win_area_gust_max.notna().mean():.1%} ({time.time() - t0:.0f}s)", flush=True)
    fitted = {}
    MODELS.mkdir(parents=True, exist_ok=True)
    for i, (arm, extra) in enumerate(ARMS.items()):
        features = base + ft.WINDOW_V1 + extra
        for s in range(args.seeds):
            path = MODELS / f"arm{i}_seed{s}.json"           # saved, so a crash later never costs a refit
            m = models.build("xgboost", PARAMS | {"random_state": s, "n_jobs": args.jobs})
            if path.exists():
                m.load_model(path)
            else:
                m.fit(train[features], train.y)
                m.save_model(path)
            fitted[(arm, s)] = (m, features)
        print(f"fitted {arm} ({time.time() - t0:.0f}s)", flush=True)
    rate = models.build("official").fit(train[official], train.y)
    del train

    test = rows([TEST_YEAR])
    actual = actual_windows([TEST_YEAR]).rename(columns={c: f"{c}|actual" for c in WINDOW})
    test = test.merge(actual[["region_fips", "block_start", "win_gust_max_ms|actual", "win_area_gust_max|actual"]],
                      on=["region_fips", "block_start"], how="left")
    f = test_forecasts()
    have = np.ones(len(test), bool)
    xs = []
    for age in AGES:
        w = run_windows(f, age)
        x = test[["region_fips", "block_start"]].merge(w, on=["region_fips", "block_start"], how="left")
        have &= x.win_gust_max_ms.notna().to_numpy()
        xs.append(x)
    del f
    keep = np.flatnonzero(have)
    test = test.iloc[keep].reset_index(drop=True)
    xs = [x.iloc[keep].reset_index(drop=True) for x in xs]
    print(f"2025: {len(test):,} decisions with all five runs, {int(test.y.sum()):,} new outages "
          f"({time.time() - t0:.0f}s)", flush=True)

    p = {"warnings + outlook": rate.predict_proba(test[official])[:, 1]}
    per_seed = {}
    for arm in ARMS:
        seeds = []
        for s in range(args.seeds):
            m, features = fitted[(arm, s)]
            runs = []
            for x in xs:
                z = test[[c for c in features if c not in WINDOW]].copy()
                z[[c for c in features if c in WINDOW]] = x[[c for c in features if c in WINDOW]].to_numpy()
                runs.append(m.predict_proba(z[features].astype("float32"))[:, 1])
            seeds.append(np.mean(runs, axis=0))
        per_seed[arm] = [ap(test.y, q) for q in seeds]
        p[arm] = np.mean(seeds, axis=0)

    day = ((storm_day(test.block_start) - storm_day(test.block_start).min()).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    boot = {k: pr_auc_resamples(test.y, v, day, counts) for k, v in p.items()}
    out = []
    for k, v in p.items():
        r = {"model": k, "onset_pr_auc": ap(test.y, v),
             "vs_warnings": ap(test.y, v) / ap(test.y, p["warnings + outlook"])}
        if k in per_seed:
            r["seed_mean"], r["seed_sd"] = np.mean(per_seed[k]), np.std(per_seed[k], ddof=1) if args.seeds > 1 else 0
        if k not in ("warnings + outlook", "headline"):
            r["diff_vs_headline"] = r["onset_pr_auc"] - ap(test.y, p["headline"])
            r["diff_lo"], r["diff_hi"] = interval(boot[k] - boot["headline"])
        out.append(r)
    out = pd.DataFrame(out)
    out["n_decisions"], out["n_outages"], out["seeds"] = len(test), int(test.y.sum()), args.seeds
    out.to_csv(RESULTS / "wind_inputs_2025.csv", index=False)
    print(out.round(4).to_string(index=False))

    by = []
    for col, label in (("win_gust_max_ms|actual", "point"), ("win_area_gust_max|actual", "county-wide")):
        b = pd.cut(test[col], GUST_BINS, right=False)
        for interval_, idx in test.groupby(b, observed=True).groups.items():
            y = test.y.loc[idx]
            r = {"gust_measured": label, "actual_gust_ms": str(interval_), "decisions": len(idx),
                 "outages": int(y.sum())}
            for k, v in p.items():
                r[k] = ap(y, v[idx]) if y.sum() else np.nan
            by.append(r)
    by = pd.DataFrame(by)
    by.to_csv(RESULTS / "wind_inputs_by_gust_2025.csv", index=False)
    print(by.round(3).to_string(index=False))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
