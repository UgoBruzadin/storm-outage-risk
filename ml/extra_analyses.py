"""Eleven follow-up analyses of the 2-hours-ahead model (docs/experiments.md, E29-E39).

Each reuses what is already computed or downloaded (the saved 2025 predictions, the HRRR forecast archive, the
warehouse) and writes ml/results/extra_<name>.csv. They run one after another; a failure in one is printed and the
next one runs.

  storm_types    E29  new outages caught by storm type at onset (warm-season convective, winter, other wind)
  severity       E30  new outages caught by how bad they got (worst share out, customers affected)
  season_hour    E31  onset PR-AUC, model vs official forecasts, by season and by time of day
  spread         E32  the five-run range as a signal: low / mean / high of the runs, and alerts on the high end
  simple_rules   E33  one-line rules (a neighbour out now, forecast gust, a warning) against the model
  thresholds     E34  the model without forecasts at >= 1% and >= 10% new outages, against the official forecasts
  delay          E35  weather arriving an hour late: the model with weather from 7 to 2 hours before the decision
  years          E36  tests on 2022, 2023, 2024 and 2025 (each trained on 2020 to the year before), and the forecast
                      model tested on 2024
  forecast_leads E37  the forecast model (newest run) at 0, 1, 3 and 6 hours ahead
  counties       E38  counties never seen in training: 5 groups of counties, trained on the others' 2020-2024
  importance     E39  onset PR-AUC lost when each input group is shuffled (2025, model without forecasts)

Usage: pixi run python -m ml.extra_analyses [--only storm_types,severity]
"""
import argparse
import traceback

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap
from sklearn.model_selection import GroupKFold

from ml import data, models
from ml import forecast_test as ft
from ml import moving_window as mw
from ml.export_hourly import HEADLINE, HEADLINE_SHARE, MODELS, predictions
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT, caught_flags, onset_hours
from ml.value_hourly import outages

RESULTS = data.ROOT / "ml" / "results"
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
LEAD = 2


def save(df, name):
    df.to_csv(RESULTS / f"extra_{name}.csv", index=False)
    print(f"--- {name}\n{df.round(4).to_string(index=False)}", flush=True)


def con():
    return duckdb.connect(str(data.DB), read_only=True)


def flagged_at_share(p, share=HEADLINE_SHARE):
    p = np.asarray(p)
    return p > np.quantile(p, 1 - share)


def official(train, test):
    cols = models.NEEDS_COLUMNS["official"]
    return models.build("official").fit(train[cols], train["y"]).predict_proba(test[cols])[:, 1]


def xgb(train, features, seed=0):
    return models.build("xgboost", PARAMS | {"random_state": seed}).fit(train[features], train["y"])


# ---------------------------------------------------------------- analyses on the saved 2025 predictions
def onsets_with_context(pred):
    """2025's new outages, whether the headline model and the official forecasts caught them (each alerting on its
    own top HEADLINE_SHARE of hours), and the conditions at the onset hour."""
    on = onset_hours(2025)
    for label in (HEADLINE, "Warnings + outlook"):
        flagged = pd.Series(flagged_at_share(pred[MODELS[label]]), index=pred.index)
        on[label] = caught_flags(pred, flagged, on, LEAD)
    c = con()
    ctx = c.sql("""
        SELECT region_fips, hour, warn_svr, warn_tor, warn_wind, warn_winter, cape_max_jkg, temp_mean_c, gust_max_ms,
               precip_sum_mm, month(hour) AS month, hour(hour) AS hour_utc
        FROM marts.mart_study__region_1h WHERE year(hour) = 2025
    """).df()
    c.close()
    on = on.merge(ctx, on=["region_fips", "hour"], how="left")
    for col in ("warn_svr", "warn_tor", "warn_wind", "warn_winter"):
        on[col] = on[col].fillna(False).astype(bool)
    winter = on.warn_winter | (on.temp_mean_c <= 2)
    convective = (on.cape_max_jkg >= 250) | on.warn_svr | on.warn_tor
    on["storm_type"] = np.where(winter, "winter / cold", np.where(convective, "warm-season convective",
                                                                   "other (wind, rain, no storm energy)"))
    return on


def storm_types(pred):
    on = onsets_with_context(pred)
    rows = []
    for kind, g in on.groupby("storm_type"):
        rows.append({"storm_type": kind, "new_outages": len(g), "caught_model": g[HEADLINE].mean(),
                     "caught_official": g["Warnings + outlook"].mean(),
                     "share_with_svr_tor_warning": (g.warn_svr | g.warn_tor).mean()})
    save(pd.DataFrame(rows), "storm_types")


def severity(pred):
    on = onsets_with_context(pred).rename(columns={"hour": "onset"})
    ev = outages([2025])
    c = con()
    worst = c.sql("""
        SELECT region_fips, hour, max(pct_out) OVER (PARTITION BY region_fips ORDER BY hour
                                                     ROWS BETWEEN CURRENT ROW AND 5 FOLLOWING) AS worst_6h
        FROM marts.mart_study__region_1h WHERE year(hour) = 2025
    """).df().rename(columns={"hour": "onset"})
    c.close()
    on = on.merge(ev[["region_fips", "onset", "affected"]], on=["region_fips", "onset"], how="left")
    on = on.merge(worst, on=["region_fips", "onset"], how="left")
    on["size"] = pd.cut(on.worst_6h, [0, 10, 25, 101], labels=["5-10% out", "10-25% out", "over 25% out"])
    on["customers"] = pd.cut(on.affected, [0, 1000, 5000, 1e9], labels=["< 1,000", "1,000-5,000", "> 5,000"])
    rows = []
    for col in ("size", "customers"):
        for level, g in on.groupby(col, observed=True):
            rows.append({"by": col, "group": str(level), "new_outages": len(g), "caught_model": g[HEADLINE].mean(),
                         "caught_official": g["Warnings + outlook"].mean()})
    save(pd.DataFrame(rows), "severity")


def season_hour(pred):
    p = pred.copy()
    local = p.block_start + pd.Timedelta(hours=LEAD) - pd.Timedelta(hours=6)       # window start, US Central (CST)
    p["season"] = local.dt.month.map({12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
                                      6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall", 11: "fall"})
    p["time"] = pd.cut(local.dt.hour, [-1, 5, 11, 17, 23], labels=["night (0-6)", "morning (6-12)",
                                                                    "afternoon (12-18)", "evening (18-24)"])
    rows = []
    for col in ("season", "time"):
        for level, g in p.groupby(col, observed=True):
            if g.y.sum() < 20:
                continue
            m, o = ap(g.y, g[MODELS[HEADLINE]]), ap(g.y, g[MODELS["Warnings + outlook"]])
            rows.append({"by": col, "group": str(level), "positive_windows": int(g.y.sum()), "rate": g.y.mean(),
                         "pr_auc_model": m, "pr_auc_official": o, "ratio": m / o})
    save(pd.DataFrame(rows), "season_hour")


def spread(pred):
    on = onset_hours(2025)
    rows = []
    for name in ("p_low", "p_mean", "p_high", "p_newest"):
        flagged = pd.Series(flagged_at_share(pred[name]), index=pred.index)
        rows.append({"signal": name, "pr_auc": ap(pred.y, pred[name]), "precision_at_share": pred.y[flagged].mean(),
                     "caught_at_share": np.mean(caught_flags(pred, flagged, on, LEAD))})
    width = pred.p_high - pred.p_low
    for k in (0.5, 1.0):
        score = pred.p_mean + k * width
        flagged = pd.Series(flagged_at_share(score), index=pred.index)
        rows.append({"signal": f"p_mean + {k} x range", "pr_auc": ap(pred.y, score),
                     "precision_at_share": pred.y[flagged].mean(),
                     "caught_at_share": np.mean(caught_flags(pred, flagged, on, LEAD))})
    save(pd.DataFrame(rows), "spread")


def simple_rules(pred):
    nb = data.neighbor_features(years=[2025])[["region_fips", "hour", "near_pct_out_max", "up_pct_out_max",
                                                "near_warn_share"]].rename(columns={"hour": "block_start"})
    p = pred.merge(nb, on=["region_fips", "block_start"], how="left")
    del nb
    w = pd.concat([ft.window_from_forecast(ft.forecasts("2024-12-31", "2025-12-31", states=[s]))[
        ["region_fips", "block_start", "win_gust_max_ms", "win_cape_max_jkg"]]
        for s in data.warehouse_states()], ignore_index=True)         # the newest run, a state at a time
    p = p.merge(w, on=["region_fips", "block_start"], how="left")
    c = con()
    warn = c.sql("SELECT region_fips, hour AS block_start, (warn_svr OR warn_tor OR warn_wind)::INT AS warned "
                 "FROM marts.mart_study__region_1h WHERE year(hour) = 2025").df()
    c.close()
    p = p.merge(warn, on=["region_fips", "block_start"], how="left")
    rules = {"a severe, tornado or wind warning in force": p.warned,
             "share of nearby counties under warning": p.near_warn_share,
             "worst outage in a county within 100 km, now": p.near_pct_out_max,
             "worst outage upwind, now": p.up_pct_out_max,
             "forecast max gust in the window (newest run)": p.win_gust_max_ms,
             "forecast max storm energy (CAPE) in the window": p.win_cape_max_jkg,
             "warnings + outlook (rate table)": p[MODELS["Warnings + outlook"]],
             "the model, last five forecasts": p[MODELS[HEADLINE]]}
    rows = [{"rule": name, "pr_auc": ap(p.y, s.fillna(-1)), "rows": int(s.notna().sum())} for name, s in rules.items()]
    save(pd.DataFrame(rows), "simple_rules")


# ---------------------------------------------------------------- analyses that retrain the model
def thresholds():
    """The model without forecasts at >= 1%, 5% and 10%: sampled training at each threshold (every window reaching
    it kept), the rate table on the full counts, 2025 scored a state at a time."""
    rows = []
    for thr in (1, 5, 10):
        fitted = mw.fit_runs([("official", "official", None), ("model", "xgboost", FEATURES)], LEAD,
                             train_years=YEARS[:-1], levels=False, threshold=thr)
        test = mw.predict_states(fitted, 2025, LEAD, threshold=thr)
        m, o = ap(test.y, test.model), ap(test.y, test.official)
        rows.append({"threshold_pct": thr, "event_rate": test.y.mean(), "pr_auc_model": m, "pr_auc_official": o,
                     "ratio": m / o, "positive_windows": int(test.y.sum())})
        del test
        print(rows[-1], flush=True)
    save(pd.DataFrame(rows), "thresholds")


def years():
    """Tests on each year from 2022, trained on 2020 to the year before (sampled training, exact rate tables, the
    test year scored a state at a time: moving_window.fit_runs / predict_states); returns the 2025 model."""
    rows, last = [], None
    for year in (2022, 2023, 2024, 2025):
        fitted = mw.fit_runs([("official", "official", None), ("model", "xgboost", FEATURES)], LEAD,
                             train_years=list(range(2020, year)), levels=False)
        test = mw.predict_states(fitted, year, LEAD)
        m, o = ap(test.y, test.model), ap(test.y, test.official)
        rows.append({"test_year": year, "model": "no forecasts", "train_years": f"2020-{year - 1}",
                     "event_rate": test.y.mean(), "positive_windows": int(test.y.sum()),
                     "pr_auc_model": m, "pr_auc_official": o, "ratio": m / o})
        print(rows[-1], flush=True)
        last = fitted["model"][0]
        del test
    # the forecast model tested on 2024: trained 2020-2023 with actual window weather, fed 2024's five runs
    early = [2020, 2021, 2022, 2023]
    wf = data.resolve_features(FEATURES) + ft.WINDOW
    train = ft.train_rows(early)
    fitted = models.build("xgboost", PARAMS).fit(train[wf], train.y, sample_weight=train.weight)
    del train
    cols = models.NEEDS_COLUMNS["official"]
    c = data.hourly_counts(THRESHOLD_PCT, early, LEAD, cols)
    off = models.build("official").fit(c[cols], c.y, sample_weight=c.weight)
    names = [f"run {k}" for k in (2, 3, 4, 5, 6)]
    ys, ps, os_ = [], [], []
    for _, val, _ in ft.states_2025(lambda f: {n: ft.window_from_forecast(f, k) for n, k in
                                               zip(names, (2, 3, 4, 5, 6), strict=True)},
                                    year=2024, require_actual=False):
        ps.append(np.column_stack([fitted.predict_proba(ft.with_version(val, wf, n))[:, 1] for n in names])
                  .mean(axis=1))
        os_.append(off.predict_proba(val[cols])[:, 1])
        ys.append(val.y.to_numpy())
        del val
    y, p, po = np.concatenate(ys), np.concatenate(ps), np.concatenate(os_)
    m, o = ap(y, p), ap(y, po)
    rows.append({"test_year": 2024, "model": "with HRRR forecasts (mean of 5 runs)", "train_years": "2020-2023",
                 "event_rate": y.mean(), "positive_windows": int(y.sum()), "pr_auc_model": m,
                 "pr_auc_official": o, "ratio": m / o})
    print(rows[-1], flush=True)
    save(pd.DataFrame(rows), "years")
    return last


def importance(fitted):
    features = data.resolve_features(FEATURES)
    test = pd.concat([rows[features + ["y"]] for _, rows in data.state_rows(THRESHOLD_PCT, 2025, LEAD)],
                     ignore_index=True)
    base = ap(test.y, fitted.predict_proba(test[features])[:, 1])
    rng = np.random.default_rng(0)
    groups = {g: [c for c in data.resolve_features(g) if c in features]
              for g in ("weather", "place", "recent_now", "warnings", "outlook", "neighbors")}
    rows = []
    for g, cols in groups.items():
        x = test[features].copy()
        x[cols] = x[cols].to_numpy()[rng.permutation(len(x))]           # shuffle the group's rows together
        s = ap(test.y, fitted.predict_proba(x)[:, 1])
        rows.append({"group": g, "columns": len(cols), "pr_auc_shuffled": s, "pr_auc_lost": base - s,
                     "share_lost": (base - s) / base})
    save(pd.DataFrame(rows).sort_values("pr_auc_lost", ascending=False), "importance")


def counties():
    """5 groups of counties, each scored on 2025 by a model trained on the other counties' 2020-2024 (sampled; the
    rate table on the other counties' full counts); 2025 scored a state at a time."""
    features = data.resolve_features(FEATURES)
    cols = models.NEEDS_COLUMNS["official"]
    train = data.sampled_years(THRESHOLD_PCT, [2020, 2021, 2022, 2023, 2024], LEAD)
    counts = data.hourly_counts(THRESHOLD_PCT, [2020, 2021, 2022, 2023, 2024], LEAD, cols + ["region_fips"])
    regions = np.array(sorted(set(train.region_fips) | set(counts.region_fips)))
    fold_of, fitted = {}, []
    for k, (_, held) in enumerate(GroupKFold(n_splits=5).split(regions, groups=regions)):
        out = set(regions[held])
        fold_of.update(dict.fromkeys(out, k))
        tr, c = train[~train.region_fips.isin(out)], counts[~counts.region_fips.isin(out)]
        fitted.append((models.build("xgboost", PARAMS).fit(tr[features], tr.y, sample_weight=tr.weight),
                       models.build("official").fit(c[cols], c.y, sample_weight=c.weight)))
        print(f"fold {k}: {len(out)} counties held out", flush=True)
    del train, counts
    parts = []
    for _, rows in data.state_rows(THRESHOLD_PCT, 2025, LEAD):
        fold = rows.region_fips.map(fold_of)
        out = rows[["region_fips", "block_start", "y"]].copy()
        out["p"], out["p_official"] = np.nan, np.nan
        for k, (model, off) in enumerate(fitted):
            sel = (fold == k).to_numpy()
            if sel.any():
                out.loc[sel, "p"] = model.predict_proba(rows.loc[sel, features])[:, 1]
                out.loc[sel, "p_official"] = off.predict_proba(rows.loc[sel, cols])[:, 1]
        parts.append(out.dropna(subset=["p"]))
        del rows
    test = pd.concat(parts, ignore_index=True)
    m, o = ap(test.y, test.p), ap(test.y, test.p_official)
    save(pd.DataFrame([{"test": "2025, counties never seen in training", "pr_auc_model": m, "pr_auc_official": o,
                        "ratio": m / o, "positive_windows": int(test.y.sum())}]), "counties")


DELAY_RAW = ["gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms", "cape_max_jkg", "precip_sum_mm",
             "precip_max_1h_mm", "temp_min_c", "temp_mean_c", "freezing_level_min_m", "icing_hours", "hail_hours"]
DELAY_NB = [f"{k}_{v}" for k in ("near", "up") for v in ("gust_max_ms", "cape_max_jkg", "precip_max_mm")]


def weather_an_hour_late(rows, year):
    """One year's decisions (any states) with every weather input from the hour before: own county and neighbours."""
    states = sorted(set(rows.region_fips.astype(str).str[:2]))
    c = con()
    w = c.sql(f"""SELECT region_fips, hour + INTERVAL 1 HOUR AS block_start, {', '.join(DELAY_RAW)}
                  FROM marts.mart_study__region_1h WHERE year(hour) BETWEEN {year - 1} AND {year}
                    AND left(region_fips, 2) IN ({", ".join(f"'{s}'" for s in states)})""").df()
    c.close()
    nb = data.neighbor_features(years=[year - 1, year], states=states)[["region_fips", "hour", *DELAY_NB]]
    nb["block_start"] = nb.pop("hour") + pd.Timedelta(hours=1)
    late = rows.drop(columns=DELAY_RAW + DELAY_NB).merge(w, on=["region_fips", "block_start"], how="left") \
               .merge(nb, on=["region_fips", "block_start"], how="left")
    return data.add_derived(late, copy=False)


def delay():
    """The model with every weather input an hour older (own county and neighbours), paired with the usual one:
    the same sampled training rows and the same 2025 decisions, the inputs swapped year by year and state by state."""
    rows = []
    for name, transform in (("on time", None), ("weather an hour late", weather_an_hour_late)):
        fitted = mw.fit_runs([("model", "xgboost", FEATURES)], LEAD, train_years=YEARS[:-1], levels=False,
                             transform=transform)
        test = mw.predict_states(fitted, 2025, LEAD, transform=transform)
        rows.append({"weather": name, "pr_auc": ap(test.y, test.model)})
        print(rows[-1], flush=True)
        del test
    save(pd.DataFrame(rows), "delay")


def forecast_leads():
    """The forecast model (newest run) at 0-6 hours ahead: sampled training with actual window weather, the rate
    table on the full counts, 2025 scored a state at a time with the run issued RUN_AGE hours before."""
    features = data.resolve_features(FEATURES) + ft.WINDOW
    cols = models.NEEDS_COLUMNS["official"]
    rows = []
    try:
        for lead in (0, 1, 2, 3, 6):
            ft.LEAD = lead                                  # the window and row functions read it
            train = ft.train_rows()
            fitted = models.build("xgboost", PARAMS).fit(train[features], train.y, sample_weight=train.weight)
            del train
            c = data.hourly_counts(THRESHOLD_PCT, ft.TRAIN_YEARS, lead, cols)
            off = models.build("official").fit(c[cols], c.y, sample_weight=c.weight)
            ys, ps, os_ = [], [], []
            for _, test, _ in ft.states_2025(lambda f: {"forecast": ft.window_from_forecast(f)},
                                             require_actual=False):
                ps.append(fitted.predict_proba(ft.with_version(test, features, "forecast"))[:, 1])
                os_.append(off.predict_proba(test[cols])[:, 1])
                ys.append(test.y.to_numpy())
                del test
            y = np.concatenate(ys)
            m, o = ap(y, np.concatenate(ps)), ap(y, np.concatenate(os_))
            rows.append({"lead_hours": lead, "pr_auc_with_forecasts": m, "pr_auc_official": o, "ratio": m / o})
            print(rows[-1], flush=True)
    finally:
        ft.LEAD = LEAD
    save(pd.DataFrame(rows), "forecast_leads")


CHEAP = {"storm_types": storm_types, "severity": severity, "season_hour": season_hour, "spread": spread,
         "simple_rules": simple_rules}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated analyses (default: all)")
    only = parser.parse_args().only
    want = set(only.split(",")) if only else None
    run = lambda name: want is None or name in want                 # noqa: E731

    def attempt(name, fn, *args):
        if not run(name):
            return None
        print(f"=== {name}", flush=True)
        try:
            return fn(*args)
        except Exception:                                           # one failure doesn't stop the rest
            traceback.print_exc()
            return None

    if any(run(n) for n in CHEAP):
        pred = predictions()
        for name, fn in CHEAP.items():
            attempt(name, fn, pred)
        del pred
    if any(run(n) for n in ("years", "importance")):
        last = attempt("years", years)
        if last is not None:
            attempt("importance", importance, last)
    attempt("counties", counties)
    attempt("delay", delay)
    attempt("thresholds", thresholds)
    attempt("forecast_leads", forecast_leads)


if __name__ == "__main__":
    main()
