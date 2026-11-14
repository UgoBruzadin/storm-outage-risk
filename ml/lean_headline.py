"""The headline test (forecast_ensemble.py's mean of five HRRR runs, 2025) with less memory, for more states.

DRAFT, not part of `pixi run pipeline`: nothing else imports this, and it changes no other file. It exists to find
out whether a leaner way of training gives the same answer as the full one, before it is trusted on more states.

What it changes, and only here:
  sampling   training keeps every decision followed by a new outage and a random NEG_FRAC of the others,
             each kept negative weighted 1 / NEG_FRAC, so the totals XGBoost sees match the full table's.
             99.5% of decisions have no new outage, so 0.1 keeps ~10% of the rows.
  one year   training years are loaded, given their window weather, sampled and shrunk one at a time: the full
             2020-2024 table is never in memory at once.
  float32    inputs are stored as 32-bit floats (XGBoost bins them anyway).
  neighbours read from the cache year by year (pyarrow filters), not the whole cache at once.
What stays the same: rows, features, labels, XGBoost settings (moving_window.PARAMS), the five run ages, the
warnings + outlook rate table (fit on the FULL counts of every training year, before sampling, so it is identical
to models.RateBaseline on the full table), the 2025 rows scored (every one, no sampling), the storm-day bootstrap
and the alert rule (each forecast's own riskiest 0.75% of 2025 decisions, as forecast_test.py's equal_share).

Inputs are arguments, so it can run on an archived warehouse while data/warehouse.duckdb holds other states:
  --db         the warehouse (default data/warehouse.duckdb)
  --neighbors  the neighbour cache made by data.neighbor_features() for that warehouse (it must exist)
  --fcst-dir   HRRR forecasts as issued, grib_to_study.py's hrrr_fcst/ (a superset of regions is fine)
  --compare    optional: forecast_ensemble.py's predictions from a full run on the same warehouse
               (data/cache/forecast_ensemble_2025.parquet); the same 2025 rows are then scored both ways

Usage:
  pixi run python -m ml.lean_headline --db data/warehouse-five-states-2026-11-07.duckdb \
      --neighbors data/_archive_five_states_2026-11-07/cache/neighbors_1h.parquet \
      --fcst-dir data/raw/_archive_five_states_2026-11-07/weather/hrrr_fcst \
      --compare data/_archive_five_states_2026-11-07/cache/forecast_ensemble_2025.parquet --tag five_states
Writes data/lean_results/lean_headline_<tag>.csv (scores), lean_predictions_<tag>.parquet, lean_log_<tag>.txt.
"""
import argparse
import resource
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from ml import data, models
from ml.forecast_ensemble import RUN_AGES
from ml.forecast_test import LEAD, TEST_YEAR, TRAIN_YEARS, window_from_forecast, window_from_hourly
from ml.forecast_test import WINDOW as ALL_WINDOW
from ml.forecast_test import WINDOW_V1 as WINDOW
from ml.metrics import score

# a record of an experiment on the Missouri + Illinois recipe: pinned to it (moving_window.FEATURES_V1)
from ml.moving_window import FEATURES_V1 as FEATURES
from ml.moving_window import PARAMS_V1 as PARAMS
from ml.moving_window import THRESHOLD_PCT, caught_flags
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

NEG_FRAC = 0.1
ALERT_SHARE = 0.0075                     # forecast_test.EQUAL_SHARE
OUT = data.ROOT / "data" / "lean_results"
OFFICIAL = models.NEEDS_COLUMNS["official"]


def peak_gb():
    """Peak resident memory of this process so far (macOS reports bytes, Linux kilobytes)."""
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e9 if sys.platform == "darwin" else r / 1e6


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')} peak {peak_gb():.1f} GB] {msg}", flush=True)


def actual_hourly(db, year):
    """forecast_test.actual_hourly for one year (+ the first hours of the next, which its last windows reach)."""
    con = duckdb.connect(str(db), read_only=True)
    hw = con.sql(f"""
        SELECT region_fips, hour, gust_ms, wind10_ms, wind850_ms, cape_jkg, precip_mm, temp_c,
               freezing_level_m, u10, v10, u500, v500
        FROM staging.stg_hrrr__hourly
        WHERE hour >= TIMESTAMP '{year}-01-01' AND hour < TIMESTAMP '{year + 1}-01-02'
    """).df()
    con.close()
    return hw


def neighbors(path, year):
    """The neighbour cache's rows for one year, as block_start."""
    t = ds.dataset(path).to_table(filter=(ds.field("hour") >= pd.Timestamp(f"{year}-01-01"))
                                  & (ds.field("hour") < pd.Timestamp(f"{year + 1}-01-01")))
    return t.to_pandas().rename(columns={"hour": "block_start"})


def forecasts(fcst_dir, regions):
    """forecast_test.forecasts from a given folder, kept to the regions scored."""
    days = pd.date_range(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31", freq="D")
    parts = []
    for d in days:
        f = pd.read_parquet(Path(fcst_dir) / f"{d:%Y%m%d}.parquet")
        parts.append(f[f.region_fips.isin(regions)])
    f = pd.concat(parts, ignore_index=True)
    f["wind10_ms"] = np.hypot(f.u10, f.v10)
    f["wind850_ms"] = np.hypot(f.u850, f.v850)
    return f


def year_rows(a, year):
    """One year's decisions as forecast_test.tables builds them: load_hourly + neighbours + actual window weather."""
    df = data.load_hourly(THRESHOLD_PCT, [year], LEAD, neighbors=False, db=a.db, states=a.states)
    df["region_fips"] = df.region_fips.astype(str)
    df = df.merge(neighbors(a.neighbors, year), on=["region_fips", "block_start"], how="left")
    return df.merge(window_from_hourly(actual_hourly(a.db, year)), on=["region_fips", "block_start"], how="left")


def onset_hours(db, year, states):
    """moving_window.onset_hours on a given warehouse: every region in it (as the original), or only `states`."""
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        SELECT region_fips, hour FROM (
            SELECT region_fips, hour, pct_out, lag(pct_out) OVER w AS before,
                   max(pct_out) OVER (w ROWS BETWEEN {data.FRESH_HOURS} PRECEDING AND 1 PRECEDING) AS recent
            FROM marts.mart_study__region_1h WHERE year(hour) BETWEEN {year - 1} AND {year}
            WINDOW w AS (PARTITION BY region_fips ORDER BY hour))
        WHERE year(hour) = {year} AND pct_out >= {THRESHOLD_PCT} AND before < {THRESHOLD_PCT}
          AND recent < {THRESHOLD_PCT}
    """).df()
    con.close()
    return (df[df.region_fips.str[:2].isin(states)] if states else df).reset_index(drop=True)


def train(a, features, rng):
    """Sampled, float32 training table, plus the official rate table from the full counts."""
    xs, ys, ws, counts = [], [], [], []
    n_full = 0
    for year in TRAIN_YEARS:
        df = year_rows(a, year)
        n_full += len(df)
        # the rate table's counts, from every row (groupby drops NaN keys, as RateBaseline's does)
        counts.append(df.groupby(OFFICIAL).y.agg(["sum", "count"]))
        keep = (df.y.to_numpy() == 1) | (rng.random(len(df)) < a.neg_frac)
        part = df.loc[keep]
        xs.append(part[features].astype(np.float32))
        ys.append(part.y.to_numpy(np.int8))
        ws.append(np.where(part.y.to_numpy() == 1, 1.0, 1.0 / a.neg_frac).astype(np.float32))
        log(f"{year}: {len(df):,} decisions, {int(df.y.sum()):,} new outages, kept {keep.sum():,}")
        del df, part
    X, y, w = pd.concat(xs, ignore_index=True), np.concatenate(ys), np.concatenate(ws)
    c = pd.concat(counts).groupby(level=list(range(len(OFFICIAL)))).sum()
    official = models.build("official")
    official.classes_ = np.array([0, 1])
    official.rates_ = (c["sum"] / c["count"]).rename("_y")
    official.rates_.index.names = OFFICIAL
    official.overall_ = float(sum(int(yy.sum()) for yy in ys) / n_full)   # every positive is kept
    log(f"training table: {len(X):,} of {n_full:,} rows, {X.memory_usage(deep=True).sum() / 1e9:.2f} GB")
    return X, y, w, official


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=data.DB)
    ap.add_argument("--neighbors", type=Path, default=data.NEIGHBOR_CACHE)
    ap.add_argument("--fcst-dir", type=Path, default=data.ROOT / "data" / "raw" / "weather" / "hrrr_fcst")
    ap.add_argument("--states", help="state FIPS codes to keep, e.g. 17,29 (default: every state in the warehouse)")
    ap.add_argument("--neg-frac", type=float, default=NEG_FRAC)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--compare", type=Path, help="a full run's forecast_ensemble_2025.parquet, same warehouse")
    ap.add_argument("--tag", default="run")
    a = ap.parse_args()
    a.states = a.states.split(",") if a.states else None
    for p in (a.db, a.neighbors, a.fcst_dir):
        if not p.exists():
            sys.exit(f"missing {p}")
    OUT.mkdir(parents=True, exist_ok=True)
    log(f"db {a.db}, neighbours {a.neighbors}, forecasts {a.fcst_dir}, states {a.states or 'all'}, "
        f"neg_frac {a.neg_frac}, seed {a.seed}")
    rng = np.random.default_rng(a.seed)
    features = data.resolve_features(FEATURES) + WINDOW

    X, y, w, official = train(a, features, rng)
    model = models.build("xgboost", {**PARAMS, "random_state": a.seed}).fit(X, y, sample_weight=w)
    del X, y, w
    log("model fitted")

    # 2025: every decision, as forecast_ensemble.py (rows where the actual window and all five runs exist)
    test = year_rows(a, TEST_YEAR)
    regions = set(test.region_fips)
    f = forecasts(a.fcst_dir, regions)
    names = [f"run {k} h before" for k in RUN_AGES]
    for n, k in zip(names, RUN_AGES, strict=True):
        wf = window_from_forecast(f, k)
        test = test.merge(wf.rename(columns={c: f"{c}|{n}" for c in ALL_WINDOW}), on=["region_fips", "block_start"],
                          how="left")
    del f
    keep = test[[f"win_gust_max_ms|{n}" for n in names] + ["win_gust_max_ms"]].notna().all(axis=1)
    test = test[keep].reset_index(drop=True)
    log(f"2025: {len(test):,} decisions with every run, {int(test.y.sum()):,} new outages")

    probs = []
    for n in names:
        x = test[features].copy()
        x[WINDOW] = test[[f"{c}|{n}" for c in WINDOW]].to_numpy()
        probs.append(model.predict_proba(x.astype(np.float32))[:, 1])
    probs = np.column_stack(probs)
    out = test[["region_fips", "block_start", "y"]].copy()
    out["p_mean"], out["p_newest"] = probs.mean(axis=1), probs[:, 0]
    out["official"] = official.predict_proba(test[OFFICIAL])[:, 1]
    del test
    out.to_parquet(OUT / f"lean_predictions_{a.tag}.parquet", index=False)

    # scores with storm-day ranges, paired, as forecast_ensemble.py / forecast_test.py
    cols = {"lean: mean of 5 runs": "p_mean", "lean: newest run": "p_newest", "warnings + outlook": "official"}
    if a.compare:
        full = pd.read_parquet(a.compare, columns=["region_fips", "block_start", "p_mean"])
        full["region_fips"] = full.region_fips.astype(str)
        out = out.merge(full.rename(columns={"p_mean": "full_p_mean"}), on=["region_fips", "block_start"],
                        how="left")
        matched = out.full_p_mean.notna()
        log(f"compare: {matched.sum():,} of {len(out):,} lean rows in the full run ({len(full):,} rows); "
            f"rank correlation {out.loc[matched, ['p_mean', 'full_p_mean']].corr('spearman').iloc[0, 1]:.4f}")
        if not matched.all():
            log("compare: scoring every forecast on the matched rows only")
            out = out[matched].reset_index(drop=True)
        cols["full: mean of 5 runs"] = "full_p_mean"
    first = pd.Timestamp(f"{TEST_YEAR - 1}-12-31")
    row_day = (storm_day(out.block_start) - first).dt.days.to_numpy()
    onsets = onset_hours(a.db, TEST_YEAR, a.states)
    counts, _ = day_weights(np.arange(max(row_day.max(), (storm_day(onsets.hour) - first).dt.days.max()) + 1))
    auc = {n: pr_auc_resamples(out.y, out[c], row_day, counts) for n, c in cols.items()}
    rows = []
    for n, c in cols.items():
        p = out[c].to_numpy()
        flagged = pd.Series(p > np.quantile(p, 1 - ALERT_SHARE), index=out.index)
        alerts = out.loc[flagged]
        r = {"forecast": n, "pr_auc": score(out.y, p)["pr_auc"]}
        r["pr_auc_lo"], r["pr_auc_hi"] = interval(auc[n])
        if n != "warnings + outlook":
            r["ratio"] = r["pr_auc"] / score(out.y, out.official)["pr_auc"]
            r["ratio_lo"], r["ratio_hi"] = interval(auc[n] / auc["warnings + outlook"])
        r["alerts_real"] = alerts.y.mean()
        r["caught"] = np.mean(caught_flags(out, flagged, onsets, LEAD))
        rows.append(r)
        log({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()})
    res = pd.DataFrame(rows)
    res["decisions"], res["new_outages"], res["neg_frac"], res["seed"] = len(out), len(onsets), a.neg_frac, a.seed
    res["peak_gb"] = round(peak_gb(), 2)
    res.to_csv(OUT / f"lean_headline_{a.tag}.csv", index=False)
    log(f"wrote {OUT / f'lean_headline_{a.tag}.csv'}")


if __name__ == "__main__":
    main()
