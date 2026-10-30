"""Integrity checks on the moving-window pipeline, before its results are published (docs/audit.md).

  timing     for a sample of 2025 decisions, recompute every input and the label from the raw
             tables with explicit time filters, and compare with what the model was given
  shift      score one raw signal (max gust, a warning in force) against the 2 h-ahead label with
             the signal moved -12 ... +12 hours: skill should peak where the signal overlaps the
             window (offset +2). A peak several hours off means two sources disagree on the clock
  shuffled   train the model on 2020-2024 with the outcomes shuffled, score on real 2025
             outcomes: anything above the base rate is a leak through the features or the pipeline
  forecast   HRRR forecast error against what happened, by forecast hour: it should grow with
             the forecast hour; if not, forecast hours are mis-indexed
  missing    what each filter drops in 2025, whether the dropped hours lean towards storms, and
             how many new outages had no decision at all that could have caught them

Usage: pixi run python -m ml.audit [--checks timing,shift,shuffled,forecast,missing]
Writes ml/results/audit_<check>.csv.
"""
import argparse

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from ml import data, models
from ml.forecast_test import forecasts
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT, onset_hours

LEAD, YEAR = 2, 2025
RESULTS = data.ROOT / "ml" / "results"
SAMPLE = 20_000


def con():
    return duckdb.connect(str(data.DB), read_only=True)


def check(rows, name, a, b, tol=1e-6):
    """Record how often two versions of the same value agree (NaN = NaN counts as agreeing)."""
    a, b = pd.Series(a, dtype=float).reset_index(drop=True), pd.Series(b, dtype=float).reset_index(drop=True)
    both_nan = a.isna() & b.isna()
    agree = both_nan | ((a - b).abs() <= tol)
    rows.append({"check": name, "n": len(a), "agree": float(agree.mean()),
                 "max_abs_diff": float((a - b).abs().max()) if (~both_nan).any() else 0.0})
    print(rows[-1], flush=True)


def timing():
    df = data.load_hourly(THRESHOLD_PCT, [YEAR], LEAD)
    s = df.sample(SAMPLE, random_state=0)[["region_fips", "block_start", "gust_max_ms", "precip_sum_mm",
                                            "pct_out_now", "max_pct_out_prev_24h", "fut_max_pct", "start_pct",
                                            "near_pct_out_max", "warn_svr", "warn_tor", "spc_cat"]]
    c = con()
    c.register("s", s)
    rows = []
    r = c.sql("""
        SELECT s.region_fips, s.block_start,
               (SELECT max(gust_ms) FROM staging.stg_hrrr__hourly w WHERE w.region_fips = s.region_fips
                  AND w.hour >= s.block_start - INTERVAL 6 HOUR AND w.hour < s.block_start)          AS gust,
               (SELECT sum(CASE WHEN precip_mm <= 100 THEN precip_mm END) FROM staging.stg_hrrr__hourly w
                  WHERE w.region_fips = s.region_fips
                  AND w.hour >= s.block_start - INTERVAL 6 HOUR AND w.hour < s.block_start)          AS precip,
               (SELECT pct_out FROM marts.mart_study__region_1h m WHERE m.region_fips = s.region_fips
                  AND m.hour = s.block_start - INTERVAL 1 HOUR)                                      AS now,
               (SELECT max(pct_out) FROM marts.mart_study__region_1h m WHERE m.region_fips = s.region_fips
                  AND m.hour >= s.block_start - INTERVAL 24 HOUR AND m.hour < s.block_start)         AS prev24,
               (SELECT CASE WHEN count(pct_out) >= 3 THEN max(pct_out) END FROM marts.mart_study__region_1h m
                  WHERE m.region_fips = s.region_fips AND m.hour >= s.block_start + INTERVAL 2 HOUR
                  AND m.hour < s.block_start + INTERVAL 8 HOUR)                                      AS fut,
               (SELECT pct_out FROM marts.mart_study__region_1h m WHERE m.region_fips = s.region_fips
                  AND m.hour = s.block_start + INTERVAL 1 HOUR)                                      AS start,
               (SELECT max(m.pct_out) FROM intermediate.int_study__region_neighbors n
                  JOIN marts.mart_study__region_1h m ON m.region_fips = n.neighbor_fips
                  WHERE n.region_fips = s.region_fips AND n.is_near
                  AND m.hour = s.block_start - INTERVAL 1 HOUR)                                      AS near_now
        FROM s ORDER BY s.region_fips, s.block_start
    """).df()
    s = s.sort_values(["region_fips", "block_start"])
    check(rows, "weather: max gust, the 6 h before the decision", s.gust_max_ms, r.gust)
    check(rows, "weather: total rain, the 6 h before the decision", s.precip_sum_mm, r.precip)
    check(rows, "outages: the hour before the decision", s.pct_out_now, r.now)
    check(rows, "outages: worst hour of the 24 h before", s.max_pct_out_prev_24h, r.prev24)
    check(rows, "neighbours: worst outage within 100 km, the hour before", s.near_pct_out_max, r.near_now)
    check(rows, "label: worst hour of h+2 ... h+7", s.fut_max_pct, r.fut)
    check(rows, "label: the hour before the window (h+1), selection only", s.start_pct, r.start)

    # warnings: every severe/tornado flag in 2025 must have a warning (county or zone) for one of the
    # region's counties, issued before the hour and not yet expired
    w = c.sql(f"""
        WITH flags AS (SELECT region_fips, hour FROM intermediate.int_study__nws_1h
                       WHERE year(hour) = {YEAR} AND (warn_svr OR warn_tor)),
        wc AS (
            SELECT st.state_fips || w.ugc_number AS fips, w.issue_utc, w.expire_utc FROM staging.stg_nws__warnings w
            JOIN seeds.study_states st USING (state_abbr) WHERE w.ugc_type = 'C' AND w.phenomena IN ('SV', 'TO')
            UNION ALL
            SELECT z.fips_code, w.issue_utc, w.expire_utc FROM staging.stg_nws__warnings w
            JOIN staging.stg_noaa__zone_county z ON z.zone_id = w.state_abbr || w.ugc_number
            WHERE w.ugc_type = 'Z' AND w.phenomena IN ('SV', 'TO'))
        SELECT f.region_fips, f.hour, EXISTS (
            SELECT 1 FROM wc WHERE list_contains(string_split(f.region_fips, '+'), wc.fips)
              AND wc.issue_utc < f.hour AND wc.expire_utc > f.hour) AS issued_before
        FROM flags f
    """).df()
    rows.append({"check": f"warnings: every {YEAR} flag has a warning issued before h, still in force",
                 "n": len(w), "agree": float(w.issued_before.mean()), "max_abs_diff": float("nan")})
    print(rows[-1], flush=True)

    o = c.sql("""
        SELECT s.region_fips, s.block_start, s.spc_cat,
               arg_max(o.spc_cat, o.issued_utc) AS recomputed, max(o.issued_utc) AS issued
        FROM s JOIN staging.stg_spc__day1_outlooks o ON o.region_fips = s.region_fips
         AND o.issued_utc < s.block_start AND s.block_start >= o.valid_from AND s.block_start < o.valid_to
        WHERE s.spc_cat IS NOT NULL GROUP BY ALL
    """).df()
    check(rows, "outlook: category from the latest product issued before h", o.spc_cat, o.recomputed)
    c.close()

    # forecasts: the run issued 2 h before, forecast hours 4-9 = the window h+2 ... h+7
    from ml.forecast_test import window_from_forecast
    f = forecasts(f"{YEAR - 1}-12-31", f"{YEAR}-12-31")
    win = window_from_forecast(f).set_index(["region_fips", "block_start"])
    pick = win.sample(2000, random_state=0)
    recomputed, runs_before = [], []
    fi = f.set_index(["region_fips", "run"])
    for (fips, h), _ in pick.iterrows():
        g = fi.loc[(fips, h - pd.Timedelta(hours=2))]
        g = g[(g.hour >= h + pd.Timedelta(hours=2)) & (g.hour < h + pd.Timedelta(hours=8))]
        recomputed.append(g.gust_ms.max() if len(g) == 6 else np.nan)
        runs_before.append(h - pd.Timedelta(hours=2) < h)
    check(rows, "forecast: max gust from the run issued at h-2, valid h+2 ... h+7", pick.win_gust_max_ms,
          recomputed, tol=1e-4)
    rows.append({"check": "forecast: run issued before the decision", "n": len(runs_before),
                 "agree": float(np.mean(runs_before)), "max_abs_diff": float("nan")})
    pd.DataFrame(rows).to_csv(RESULTS / "audit_timing.csv", index=False)


def shift():
    df = data.load_hourly(THRESHOLD_PCT, [YEAR], LEAD, neighbors=False)[["region_fips", "block_start", "y"]]
    c = con()
    hw = c.sql(f"""SELECT region_fips, hour, gust_ms FROM staging.stg_hrrr__hourly
                   WHERE hour BETWEEN TIMESTAMP '{YEAR - 1}-12-30' AND TIMESTAMP '{YEAR + 1}-01-02'""").df()
    warn = c.sql(f"""SELECT region_fips, hour, (warn_svr OR warn_tor)::INT AS warn FROM intermediate.int_study__nws_1h
                     WHERE hour BETWEEN TIMESTAMP '{YEAR - 1}-12-30' AND TIMESTAMP '{YEAR + 1}-01-02'""").df()
    c.close()
    gust = hw.pivot(index="hour", columns="region_fips", values="gust_ms").asfreq("h")
    w = warn.pivot(index="hour", columns="region_fips", values="warn").reindex(gust.index).fillna(0)
    roll_gust = gust.rolling(6, min_periods=6).max()            # row t = hours t-5 ... t
    roll_warn = w.rolling(6, min_periods=1).max()
    rows = []
    for offset in range(-12, 13):
        # the 6 hours starting at decision + offset end at decision + offset + 5
        at = df.block_start + pd.Timedelta(hours=offset + 5)
        for name, table in (("max gust over 6 h", roll_gust), ("severe/tornado warning in 6 h", roll_warn)):
            stacked = table.stack().rename("v")
            v = stacked.reindex(pd.MultiIndex.from_arrays([at, df.region_fips])).to_numpy()
            ok = ~np.isnan(v)
            rows.append({"signal": name, "offset_hours": offset,
                         "pr_auc": average_precision_score(df.y[ok], v[ok]), "n": int(ok.sum())})
        print(rows[-2:], flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "audit_shift.csv", index=False)
    print(out.loc[out.groupby("signal").pr_auc.idxmax()])


def shuffled():
    df = data.load_hourly(THRESHOLD_PCT, [2020, 2021, 2022, 2023, 2024, YEAR], LEAD)
    train, test = df[df.year < YEAR], df[df.year == YEAR]
    features = data.resolve_features(FEATURES)
    rows = []
    for seed in (0, 1):
        y = np.random.default_rng(seed).permutation(train["y"].to_numpy())
        p = models.build("xgboost", PARAMS).fit(train[features], y).predict_proba(test[features])[:, 1]
        rows.append({"seed": seed, "pr_auc_shuffled_training": average_precision_score(test["y"], p),
                     "base_rate": float(test["y"].mean())})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(RESULTS / "audit_shuffled.csv", index=False)


def forecast():
    f = forecasts(f"{YEAR - 1}-12-31", f"{YEAR}-12-31")
    f["wind10_ms"] = np.hypot(f.u10, f.v10)
    c = con()
    a = c.sql(f"""SELECT region_fips, hour, gust_ms, wind10_ms, cape_jkg, precip_mm, temp_c
                  FROM staging.stg_hrrr__hourly WHERE year(hour) = {YEAR}""").df()
    c.close()
    m = f.merge(a, on=["region_fips", "hour"], suffixes=("_f", "_a"))
    rows = []
    for fh, g in m.groupby("fhour"):
        r = {"fhour": int(fh), "n": len(g)}
        for v in ("gust_ms", "wind10_ms", "cape_jkg", "precip_mm", "temp_c"):
            r[f"{v}_mae"] = float((g[f"{v}_f"] - g[f"{v}_a"]).abs().mean())
            r[f"{v}_bias"] = float((g[f"{v}_f"] - g[f"{v}_a"]).mean())
        storm = g.gust_ms_a >= 15
        r["gust_corr_when_gusty"] = float(g.loc[storm, "gust_ms_f"].corr(g.loc[storm, "gust_ms_a"]))
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "audit_forecast.csv", index=False)
    print(out.round(3).to_string())


def missing():
    c = con()
    s = c.sql(f"""
        WITH m AS (
            SELECT m.*, c.tracked, (m.hour - INTERVAL 12 HOUR)::DATE AS day
            FROM marts.mart_study__region_1h m
            LEFT JOIN marts.mart_study__region_coverage c ON c.region_fips = m.region_fips AND c.year = year(m.hour)
            WHERE year(m.hour) = {YEAR}
        ),
        days AS (SELECT day, max(pct_out) AS worst FROM m GROUP BY 1),
        storm_days AS (SELECT day FROM days WHERE worst >= 20)
        SELECT (day IN (SELECT day FROM storm_days)) AS storm_day,
               count(*) AS region_hours,
               avg((NOT coalesce(tracked, false))::INT) AS share_untracked,
               avg((NOT has_weather)::INT) AS share_no_weather,
               avg((fut_max_pct_2 IS NULL)::INT) AS share_label_unknown,
               avg((pct_out IS NULL)::INT) AS share_outage_unknown
        FROM m GROUP BY 1 ORDER BY 1
    """).df()
    c.close()
    print(s.round(4).to_string())
    pred = pd.read_parquet(data.ROOT / "data" / "cache" / "forecast_ensemble_2025.parquet",
                           columns=["region_fips", "block_start"])
    on = onset_hours(YEAR)
    reachable = set()
    for offset in range(LEAD, LEAD + 6):
        reachable |= set(zip(pred.region_fips, pred.block_start + pd.Timedelta(hours=offset), strict=True))
    on["reachable"] = [(r, h) in reachable for r, h in zip(on.region_fips, on.hour, strict=True)]
    print(f"new outages with at least one scored decision that could have caught them: "
          f"{on.reachable.sum()} of {len(on)} ({on.reachable.mean():.1%})")
    s["new_outages"], s["new_outages_reachable"] = len(on), int(on.reachable.sum())
    s.to_csv(RESULTS / "audit_missing.csv", index=False)


CHECKS = {"timing": timing, "shift": shift, "shuffled": shuffled, "forecast": forecast, "missing": missing}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checks", default=",".join(CHECKS))
    for name in parser.parse_args().checks.split(","):
        print(f"=== {name}", flush=True)
        CHECKS[name]()
