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
    # the model's rows are 32-bit floats (data.shrink): allow their rounding (~1e-7 relative) on top of tol. A real
    # timing or join error moves a value by whole units, far beyond this
    agree = both_nan | ((a - b).abs() <= tol + 1e-6 * b.abs())
    rows.append({"check": name, "n": len(a), "agree": float(agree.mean()),
                 "max_abs_diff": float((a - b).abs().max()) if (~both_nan).any() else 0.0})
    print(rows[-1], flush=True)


TIMING_COLS = ["region_fips", "block_start", "gust_max_ms", "precip_sum_mm", "pct_out_now", "max_pct_out_prev_24h",
               "fut_max_pct", "start_pct", "near_pct_out_max", "warn_svr", "warn_tor", "spc_cat",
               # E55's inputs (data.add_static), checked against their sources
               "precip_prev_72h_mm", "hist_events_per_year", "hist_storm_hit_rate", "lat", "lon",
               "log_customers", "log_road_per_customer", "road_treed_share", "tm_height_ft", "soil_poor_drain_share",
               "util_saidi", "flood_zone_share", "poor_drain_x_rain"]


def sample_decisions(n, seed=0):
    """A uniform sample of n scored decisions of YEAR, drawn a state at a time (each state's share of n is its share
    of the decisions), so the whole country's year is never in memory at once."""
    total = data.hourly_counts(THRESHOLD_PCT, [YEAR], LEAD, ["warn_svr"]).weight.sum()
    parts = []
    for i, (_, rows) in enumerate(data.state_rows(THRESHOLD_PCT, [YEAR][0], LEAD)):
        k = min(len(rows), round(n * len(rows) / total))
        parts.append(rows[TIMING_COLS].sample(k, random_state=seed + i))
        del rows
    return pd.concat(parts, ignore_index=True)


def static_from_files(rows, s):
    """Each place input on the decision equals its county's value in the source file (a join on the wrong key, or one
    that reorders rows, would put another county's value on the row)."""
    place = data.ROOT / "data" / "raw" / "place"
    src = (pd.read_csv(place / "roads.csv", dtype={"region_fips": str})
           .merge(pd.read_csv(data.GEO_FILE, dtype={"region_fips": str}), on="region_fips")
           .merge(pd.read_csv(place / "treemap.csv", dtype={"region_fips": str}), on="region_fips")
           .merge(pd.read_csv(place / "soil.csv", dtype={"region_fips": str}), on="region_fips")
           .merge(pd.read_csv(place / "utilities.csv", dtype={"region_fips": str}), on="region_fips")
           .merge(pd.read_csv(place / "flood_zones.csv", dtype={"region_fips": str}), on="region_fips", how="left"))
    m = s[["region_fips", "log_customers", "precip_prev_72h_mm"]].merge(src, on="region_fips", how="left")
    check(rows, "place: latitude from regions_study.csv", s.lat, m.lat, tol=1e-4)
    check(rows, "place: longitude from regions_study.csv", s.lon, m.lon, tol=1e-4)
    check(rows, "place: road per customer from roads.csv", s.log_road_per_customer,
          np.log10(m.road_km) - m.log_customers, tol=1e-4)
    check(rows, "place: road under canopy from roads.csv", s.road_treed_share, m.road_treed_share, tol=1e-5)
    check(rows, "place: tree height from treemap.csv", s.tm_height_ft, m.tm_height_ft, tol=1e-3)
    check(rows, "place: poorly drained soil from soil.csv", s.soil_poor_drain_share, m.soil_poor_drain_share, tol=1e-5)
    check(rows, "place: utility SAIDI from utilities.csv", s.util_saidi, m.util_saidi, tol=1e-2)
    check(rows, "place: flood zone share from flood_zones.csv", s.flood_zone_share, m.flood_zone_share, tol=1e-5)
    check(rows, "place: poorly drained soil x 72 h rain", s.poor_drain_x_rain,
          m.soil_poor_drain_share * m.precip_prev_72h_mm, tol=1e-2)


def timing():
    s = sample_decisions(SAMPLE)
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
                  AND m.hour = s.block_start - INTERVAL 1 HOUR)                                      AS near_now,
               (SELECT CASE WHEN count(CASE WHEN precip_mm <= 100 THEN precip_mm END) = 72
                            THEN sum(CASE WHEN precip_mm <= 100 THEN precip_mm END) END
                  FROM staging.stg_hrrr__hourly w WHERE w.region_fips = s.region_fips
                  AND w.hour >= s.block_start - INTERVAL 72 HOUR AND w.hour < s.block_start)         AS rain72,
               (SELECT events_per_year FROM marts.mart_study__region_history_asof h
                  WHERE h.region_fips = s.region_fips AND h.as_of_year = year(s.block_start))        AS hist_events,
               (SELECT storm_hit_rate FROM marts.mart_study__region_history_asof h
                  WHERE h.region_fips = s.region_fips AND h.as_of_year = year(s.block_start))        AS hist_hit,
               (SELECT max(history_end) <= date_trunc('year', s.block_start)
                  FROM marts.mart_study__region_history_asof h
                  WHERE h.region_fips = s.region_fips AND h.as_of_year = year(s.block_start))        AS hist_before
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
    check(rows, "weather: total rain, the 72 h before the decision", s.precip_prev_72h_mm, r.rain72, tol=1e-2)
    check(rows, "history: events per year, as of Jan 1 of the row's year", s.hist_events_per_year, r.hist_events,
          tol=1e-4)
    check(rows, "history: storm hit rate, as of Jan 1 of the row's year", s.hist_storm_hit_rate, r.hist_hit, tol=1e-4)
    rows.append({"check": "history: ends on or before Jan 1 of the row's year", "n": len(r),
                 "agree": float(r.hist_before.fillna(True).mean()), "max_abs_diff": float("nan")})
    print(rows[-1], flush=True)
    static_from_files(rows, s)

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

    # forecasts: the run issued 2 h before, forecast hours 4-9 = the window h+2 ... h+7; ~2,000 windows, drawn a
    # state at a time in proportion to its counties
    from ml.forecast_test import window_from_forecast
    states = data.warehouse_states()
    c = con()
    per_state = dict(c.sql("SELECT left(region_fips, 2), count(DISTINCT region_fips) FROM marts.mart_study__region_1h "
                           "GROUP BY 1").fetchall())
    c.close()
    picked, recomputed, runs_before = [], [], []
    dur_picked, dur_recomputed = [], []
    for i, st in enumerate(states):
        f = forecasts(f"{YEAR - 1}-12-31", f"{YEAR}-12-31", states=[st])
        if f.empty:
            continue
        win = window_from_forecast(f).set_index(["region_fips", "block_start"])
        pick = win.sample(min(len(win), round(2000 * per_state[st] / sum(per_state.values()))), random_state=i)
        fi = f.set_index(["region_fips", "run"]).sort_index()
        for (fips, h), _ in pick.iterrows():
            g = fi.loc[(fips, h - pd.Timedelta(hours=2))]
            g = g[(g.hour >= h + pd.Timedelta(hours=2)) & (g.hour < h + pd.Timedelta(hours=8))]
            recomputed.append(g.gust_ms.max() if len(g) == 6 else np.nan)
            full = len(g) == 6
            dur_recomputed.append({"win_gust_hours15": (g.gust_ms >= 15).sum() if full else np.nan,
                                   "win_gust_hours20": (g.gust_ms >= 20).sum() if full else np.nan,
                                   "win_gust_mean": g.gust_ms.mean() if full else np.nan,
                                   "win_gust_median": g.gust_ms.median() if full else np.nan,
                                   "win_gustiness_max": (g.gust_ms - g.wind10_ms).max() if full else np.nan})
            runs_before.append(h - pd.Timedelta(hours=2) < h)
        picked.append(pick.win_gust_max_ms)
        dur_picked.append(pick[list(dur_recomputed[0])])
        del f, win, fi
    check(rows, "forecast: max gust from the run issued at h-2, valid h+2 ... h+7", pd.concat(picked),
          recomputed, tol=1e-4)
    rows.append({"check": "forecast: run issued before the decision", "n": len(runs_before),
                 "agree": float(np.mean(runs_before)), "max_abs_diff": float("nan")})
    got, want = pd.concat(dur_picked), pd.DataFrame(dur_recomputed)
    for c in want:
        check(rows, f"forecast: {c} from the run issued at h-2, valid h+2 ... h+7", got[c], want[c], tol=1e-4)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "audit_timing.csv", index=False)
    bad = out[out.agree < 1]
    if len(bad):
        raise SystemExit(f"timing audit: {len(bad)} checks disagree:\n{bad.to_string(index=False)}")


def shift():
    df = pd.concat([rows[["region_fips", "block_start", "y"]] for _, rows in
                    data.state_rows(THRESHOLD_PCT, YEAR, LEAD, neighbors=False)], ignore_index=True)
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
    """Labels shuffled across the (sampled) training rows, unweighted: they no longer depend on the inputs, so any
    2025 PR-AUC above the base rate is a leak. 2025 scored in full, a state at a time."""
    from ml.moving_window import predict_states
    train = data.sampled_years(THRESHOLD_PCT, [2020, 2021, 2022, 2023, 2024], LEAD)
    features = data.resolve_features(FEATURES)
    fitted = {}
    for seed in (0, 1):
        y = np.random.default_rng(seed).permutation(train["y"].to_numpy())
        fitted[seed] = (models.build("xgboost", PARAMS).fit(train[features], y), features, None)
    del train
    test = predict_states(fitted, YEAR, LEAD, keep=("y",))
    rows = []
    for seed in (0, 1):
        rows.append({"seed": seed, "pr_auc_shuffled_training": average_precision_score(test["y"], test[seed]),
                     "base_rate": float(test["y"].mean())})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(RESULTS / "audit_shuffled.csv", index=False)


def forecast():
    """Forecast error by forecast hour, summed a state at a time (sums, so the means and the correlation are exact)."""
    variables = ("gust_ms", "wind10_ms", "cape_jkg", "precip_mm", "temp_c")
    sums = []
    for st in data.warehouse_states():
        f = forecasts(f"{YEAR - 1}-12-31", f"{YEAR}-12-31", states=[st])
        if f.empty:
            continue
        c = con()
        a = c.sql(f"""SELECT region_fips, hour, gust_ms, wind10_ms, cape_jkg, precip_mm, temp_c
                      FROM staging.stg_hrrr__hourly WHERE year(hour) = {YEAR} AND left(region_fips, 2) = '{st}'""").df()
        c.close()
        m = f.merge(a, on=["region_fips", "hour"], suffixes=("_f", "_a"))
        del f, a
        d = pd.DataFrame({"fhour": m.fhour, "n": 1.0})
        for v in variables:
            err = m[f"{v}_f"] - m[f"{v}_a"]
            d[f"{v}_n"], d[f"{v}_abs"], d[f"{v}_err"] = err.notna().astype(float), err.abs(), err
        storm = m.gust_ms_a >= 15
        x, y = m.gust_ms_f.where(storm), m.gust_ms_a.where(storm)
        ok = (x.notna() & y.notna()).astype(float)
        d["g_n"], d["g_x"], d["g_y"] = ok, x.where(ok > 0), y.where(ok > 0)
        d["g_xx"], d["g_yy"], d["g_xy"] = d.g_x ** 2, d.g_y ** 2, d.g_x * d.g_y
        sums.append(d.groupby("fhour").sum(min_count=1))
        del m, d
    s = pd.concat(sums).groupby(level=0).sum(min_count=1)
    rows = []
    for fh, g in s.iterrows():
        r = {"fhour": int(fh), "n": int(g.n)}
        for v in variables:
            r[f"{v}_mae"] = float(g[f"{v}_abs"] / g[f"{v}_n"])
            r[f"{v}_bias"] = float(g[f"{v}_err"] / g[f"{v}_n"])
        n = g.g_n
        cov = g.g_xy / n - (g.g_x / n) * (g.g_y / n)
        var_x, var_y = g.g_xx / n - (g.g_x / n) ** 2, g.g_yy / n - (g.g_y / n) ** 2
        r["gust_corr_when_gusty"] = float(cov / np.sqrt(var_x * var_y))
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
    # (region, hour) as one integer each, so the whole country's decisions don't become a Python set of tuples
    codes = {r: i for i, r in enumerate(sorted(set(pred.region_fips.astype(str)) | set(on.region_fips.astype(str))))}

    def key(regions, hours):
        h = (pd.to_datetime(hours) - pd.Timestamp("2000-01-01")) // pd.Timedelta(hours=1)
        return regions.astype(str).map(codes).to_numpy(dtype=np.int64) * 1_000_000 + h.to_numpy(dtype=np.int64)

    base = key(pred.region_fips, pred.block_start)
    reachable = np.unique(np.concatenate([base + offset for offset in range(LEAD, LEAD + 6)]))
    on["reachable"] = np.isin(key(on.region_fips, on.hour), reachable)
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
