"""How much of the perfect-weather ceiling can HRRR forecasts deliver? (docs/experiments.md, E19)

The forecast-ready model (moving_window.py) knows only weather that has already happened. Here it
also gets the weather of the window it predicts, summarized the same way (max gust, total rain, ...
over the 6 hours), trained with the weather that actually happened (Open-Meteo, 2020-2024) and
scored on 2025 with three versions of that window weather:

  actual     what happened (Open-Meteo): the ceiling
  1 h fcst   each hour from the HRRR run issued one hour before it (hrrrzarr): a control for the
             change of data source, since Open-Meteo stitches runs its own way
  forecast   the HRRR run issued 2 hours before the decision (complete by then), forecast hours
             LEAD + 2 ... LEAD + 7: what a utility would have had

The model is trained on actual weather only, so it needs forecasts for 2025 only. The warnings +
outlook rate table and the forecast-ready model without window weather are scored on the same rows.

Every score comes with a 95% range from a paired bootstrap over 2025's storm days (ml/uncertainty.py).
Alerts are reported two ways: at each model's level fixed on 2024 (actual weather), as in
moving_window.py, and at one shared alert share, so that versions alerting more often don't look
better just for that.

Usage: pixi run python -m ml.forecast_test [--from-cache]
Writes ml/results/forecast_test_2025.csv and the predictions to data/cache/. Needs
ingest/fetch_hrrr_forecast.py for 2024-12-31 .. 2025-12-31.
"""
import argparse
import hashlib
import json
import sys

import duckdb
import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ml import data, models
from ml.metrics import score, weighted_quantile
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT, caught_flags, episodes, onset_hours
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

LEAD = 2
RUN_AGE = 2                                   # hours between a run's issue time and the decision
TRAIN_YEARS, VAL_YEAR, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2024, 2025
EQUAL_SHARE = 0.0075                          # the forecast-ready model's alert share at its frozen level
FCST_DIR = data.ROOT / "data" / "raw" / "weather" / "hrrr_fcst"
FCST_BY_STATE = data.ROOT / "data" / "cache" / "hrrr_fcst_by_state"
PREDICTIONS = data.ROOT / "data" / "cache" / "forecast_test_2025_predictions.parquet"
HOURLY = ["gust_ms", "wind10_ms", "wind850_ms", "shear_ms", "cape_jkg", "precip_mm", "temp_c",
          "freezing_level_m", "icing", "hail", "g15", "g20", "gustiness"]
WINDOW_V1 = ["win_gust_max_ms", "win_wind10_max_ms", "win_wind850_max_ms", "win_shear_0_6km_max_ms",
          "win_cape_max_jkg", "win_precip_sum_mm", "win_precip_max_1h_mm", "win_temp_min_c", "win_temp_mean_c",
          "win_freezing_level_min_m", "win_icing_hours", "win_hail_hours",
          "win_wind_x_precip", "win_wind_squared", "win_shear_x_cape"]
# E55: how long and how evenly the wind blows over the window (+2.1% on the USA 2024, ml/usa_ablation.py)
DURATION = ["win_gust_hours15", "win_gust_hours20", "win_gust_mean", "win_gust_median", "win_gustiness_max"]
WINDOW = WINDOW_V1 + DURATION            # every window input: swapped for each forecast run's when scoring


def prepare(hw):
    """Per-hour inputs to the 6-hour summaries, as in mart_study__region_1h."""
    hw = hw.copy()
    hw.loc[hw.precip_mm > 100, "precip_mm"] = np.nan                  # archive artifact (E14)
    hw["shear_ms"] = np.hypot(hw.u500 - hw.u10, hw.v500 - hw.v10)
    hw["icing"] = ((hw.temp_c <= 0) & (hw.precip_mm > 0)).astype(float)
    hw["hail"] = ((hw.cape_jkg >= 500) & (hw.precip_mm >= 2) & (hw.freezing_level_m <= 3500)).astype(float)
    hw.loc[hw.gust_ms.isna(), ["icing", "hail"]] = np.nan
    hw["g15"] = (hw.gust_ms >= 15).astype(float).where(hw.gust_ms.notna())         # duration / spread (E55)
    hw["g20"] = (hw.gust_ms >= 20).astype(float).where(hw.gust_ms.notna())
    hw["gustiness"] = hw.gust_ms - hw.wind10_ms
    return hw


def summarize(g):
    """The 6-hour summaries from an aggregator over one window's hours (rolling or groupby)."""
    out = pd.DataFrame({
        "win_gust_max_ms": g["gust_ms"].max(), "win_wind10_max_ms": g["wind10_ms"].max(),
        "win_wind850_max_ms": g["wind850_ms"].max(), "win_shear_0_6km_max_ms": g["shear_ms"].max(),
        "win_cape_max_jkg": g["cape_jkg"].max(), "win_precip_sum_mm": g["precip_mm"].sum(),
        "win_precip_max_1h_mm": g["precip_mm"].max(), "win_temp_min_c": g["temp_c"].min(),
        "win_temp_mean_c": g["temp_c"].mean(), "win_freezing_level_min_m": g["freezing_level_m"].min(),
        "win_icing_hours": g["icing"].sum(), "win_hail_hours": g["hail"].sum(),
        "win_gust_hours15": g["g15"].sum(), "win_gust_hours20": g["g20"].sum(), "win_gust_mean": g["gust_ms"].mean(),
        "win_gust_median": g["gust_ms"].median(), "win_gustiness_max": g["gustiness"].max(),
    })
    out.loc[g["gust_ms"].count() < 6] = np.nan                           # all 6 hours or unknown
    out["win_wind_x_precip"] = out.win_gust_max_ms * out.win_precip_sum_mm
    out["win_wind_squared"] = out.win_gust_max_ms ** 2
    out["win_shear_x_cape"] = out.win_shear_0_6km_max_ms * out.win_cape_max_jkg
    return out[WINDOW]


def window_from_hourly(hw):
    """For each decision hour h: the summaries over hours h + LEAD ... h + LEAD + 5."""
    hw = prepare(hw)
    parts = []
    for fips, r in hw.groupby("region_fips"):
        r = r.set_index("hour").sort_index()
        r = r.reindex(pd.date_range(r.index.min(), r.index.max(), freq="h"))
        s = summarize(r[HOURLY].rolling(6, min_periods=1))           # covers t-5 ... t
        s.index = s.index - pd.Timedelta(hours=LEAD + 5)                # ... = h + LEAD ... h + LEAD + 5
        parts.append(s.assign(region_fips=fips))
    return pd.concat(parts).rename_axis("block_start").reset_index()


def actual_hourly(years, states=None, until=None):
    """The weather each hour turned out to be, from the first of `years` through the year after the last.
    states: only these states' regions; until: stop before this hour (a window needs only 7 hours past a year)."""
    con = duckdb.connect(str(data.DB), read_only=True)
    hw = con.sql(f"""
        SELECT region_fips, hour, gust_ms, wind10_ms, wind850_ms, cape_jkg, precip_mm, temp_c,
               freezing_level_m, u10, v10, u500, v500
        FROM staging.stg_hrrr__hourly
        WHERE year(hour) BETWEEN {min(years)} AND {max(years) + 1}
          {f"AND hour < TIMESTAMP '{until}'" if until else ""}
          {"AND left(region_fips, 2) IN (" + ", ".join(f"'{s}'" for s in states) + ")" if states else ""}
    """).df()
    con.close()
    return hw


def forecasts(start, end, states=None, source=FCST_DIR):
    """HRRR runs as issued from `start` to `end`. states: only these states' regions, read from a copy of the
    daily files split by state (built once), so one state's year of runs is read without the whole country's.
    source: the folder of daily files (default the point forecasts; forecast_training reads hrrr_grib_area)."""
    days = pd.date_range(start, end, freq="D")
    if states is None:
        f = pd.concat([pd.read_parquet(source / f"{d:%Y%m%d}.parquet") for d in days], ignore_index=True)
    else:
        folder = _forecasts_by_state(days, source)
        parts = [pd.read_parquet(folder / f"{s}.parquet") for s in states if (folder / f"{s}.parquet").exists()]
        f = (pd.concat(parts, ignore_index=True) if parts
             else pd.read_parquet(next(source / f"{d:%Y%m%d}.parquet" for d in days
                                       if (source / f"{d:%Y%m%d}.parquet").exists())).head(0))
    f["wind10_ms"] = np.hypot(f.u10, f.v10)
    f["wind850_ms"] = np.hypot(f.u850, f.v850)
    return f


def _forecasts_by_state(days, source=FCST_DIR):
    """data/cache/<source>_by_state/<first>_<last>/<state>.parquet: the daily forecast files rewritten one file per
    state, in one pass over the days. Rebuilt when any daily file changes (size or time); days without a file
    (runs missing from the archive) are left out."""
    folder = (FCST_BY_STATE if source == FCST_DIR else FCST_BY_STATE.with_name(f"{source.name}_by_state")) \
        / f"{days[0]:%Y%m%d}_{days[-1]:%Y%m%d}"
    sources = [p for p in (source / f"{d:%Y%m%d}.parquet" for d in days) if p.exists()]
    stamp = {p.name: [p.stat().st_size, p.stat().st_mtime] for p in sources}
    marker = folder / "_built_from.json"
    if marker.exists() and json.loads(marker.read_text()) == stamp:
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.parquet*"):
        old.unlink()
    marker.unlink(missing_ok=True)
    writers = {}
    for i, p in enumerate(sources):
        t = pq.read_table(p)
        state = pc.utf8_slice_codeunits(t["region_fips"], 0, 2)
        for s in pc.unique(state).to_pylist():
            part = t.filter(pc.equal(state, s))
            if s not in writers:
                writers[s] = pq.ParquetWriter(folder / f"{s}.parquet.tmp", part.schema)
            writers[s].write_table(part.cast(writers[s].schema))
        if (i + 1) % 50 == 0:
            print(f"forecasts by state: {i + 1}/{len(sources)} days", flush=True)
    for s, w in writers.items():
        w.close()
        (folder / f"{s}.parquet.tmp").rename(folder / f"{s}.parquet")
    marker.write_text(json.dumps(stamp))
    return folder


def window_from_forecast(f, run_age=RUN_AGE):
    """For each decision hour h: the run issued run_age hours before h, forecast hours for h + LEAD ... + 5."""
    first = run_age + LEAD
    f = prepare(f[f.fhour.between(first, first + 5)])
    s = summarize(f.groupby(["region_fips", "run"]))
    s = s.reset_index()
    s["block_start"] = s.pop("run") + pd.Timedelta(hours=run_age)
    return s


def actual_window(year, states=None):
    """The window weather that actually happened, for every decision hour of `year` and every region: built once
    per year and lead for the whole country (data.cached) and read back for the states asked for."""
    def build():
        w = window_from_hourly(actual_hourly([year], until=f"{year + 1}-01-02"))
        w = w[w.block_start.dt.year == year]
        w.insert(0, "state", w.region_fips.str[:2])
        return data.shrink(w.reset_index(drop=True))
    w = data.cached("actual_window", {"year": year, "lead": LEAD}, build, code_files=(data.__file__, __file__),
                    filters=[("state", "in", list(states))] if states else None)
    return w.drop(columns="state")


def add_actual_window(df, year):
    """One year's decisions + the window weather that actually happened (data.sampled_years' `add`)."""
    df["region_fips"] = df.region_fips.astype(str)
    return df.merge(actual_window(year), on=["region_fips", "block_start"], how="left", validate="m:1")


def train_rows(years=TRAIN_YEARS, onsets_only=True):
    """The training decisions with the window weather that actually happened, built one year at a time and
    sampled (data.NEG_FRAC; the `weight` column restores the full table's totals): the whole country's training
    years never have to be in memory at once."""
    return data.sampled_years(THRESHOLD_PCT, years, LEAD, add=add_actual_window, onsets_only=onsets_only)


def states_2025(make_versions, onsets=True, every=False, year=TEST_YEAR, require_actual=True):
    """A scored year (2025 unless `year` says otherwise), one state at a time: yields (state, scored, shown).
    `scored` = the onset decisions (as scored everywhere) that have every version's window weather and (if
    require_actual) the actual one, `shown` = every decision with every version (for maps; None unless
    every=True). Each version's window weather is in `<feature>|<version>`. Never sampled.
    make_versions: forecasts -> {name: window table} (window_from_hourly / window_from_forecast)."""
    for s in data.warehouse_states():
        versions = window_versions(make_versions, year, s)
        if versions is None:
            print(f"{data.STATE_ABBR.get(s, s)}: no HRRR forecasts, skipped", flush=True)
            continue
        actual = actual_window(year, states=[s])
        scored = shown = None
        if onsets:
            rows = data.load_hourly(THRESHOLD_PCT, [year], LEAD, states=[s], float32=True)
            scored = with_windows(rows, actual, versions, require_actual=require_actual)
            print(f"{data.STATE_ABBR.get(s, s)}: {year} decisions with every version: {len(scored):,} of "
                  f"{len(rows):,}", flush=True)
            if scored.empty:
                continue
        if every:
            shown = with_windows(data.load_hourly(THRESHOLD_PCT, [year], LEAD, onsets_only=False, states=[s],
                                                  float32=True), actual, versions, require_actual=False)
        yield s, scored, shown


def window_versions(make_versions, year, state):
    """make_versions(forecasts) for one state's year of HRRR runs, built once and cached (data.cached): reading the
    runs and summarizing five of them is the slowest part of scoring a year, and every step that scores 2025 needs
    the same tables. The key covers the forecast files (a new download rebuilds it) and the code that makes them.
    Returns {version: window table}, or None when the state has no forecasts."""
    days = pd.date_range(f"{year - 1}-12-31", f"{year}-12-31", freq="D")
    marker = _forecasts_by_state(days) / "_built_from.json"
    fn = f"{make_versions.__module__}.{make_versions.__qualname__}"

    def build():
        f = forecasts(days[0], days[-1], states=[state])
        if f.empty:
            return pd.DataFrame({"version": pd.Series(dtype=str)})
        v = make_versions(f)
        del f
        return data.shrink(pd.concat([w.assign(version=n) for n, w in v.items()], ignore_index=True))

    code = (data.__file__, __file__, sys.modules[make_versions.__module__].__file__)
    t = data.cached("window_versions", {"year": year, "state": state, "versions": fn,
                                        "forecasts": hashlib.sha1(marker.read_bytes()).hexdigest()},
                    build, code_files=code)
    if t.empty:
        return None
    return {n: g.drop(columns="version").reset_index(drop=True) for n, g in t.groupby("version", sort=False)}


def with_windows(rows, actual, versions, require_actual):
    """Decisions + the actual window weather + each version's as `<feature>|<version>`, keeping the decisions
    that have every version (and the actual weather, if require_actual)."""
    rows["region_fips"] = rows.region_fips.astype(str)
    rows = rows.merge(actual, on=["region_fips", "block_start"], how="left", validate="m:1")
    for name, w in versions.items():
        rows = rows.merge(w.rename(columns={c: f"{c}|{name}" for c in WINDOW}),
                          on=["region_fips", "block_start"], how="left", validate="m:1")
    need = [f"win_gust_max_ms|{n}" for n in versions] + (["win_gust_max_ms"] if require_actual else [])
    return rows[rows[need].notna().all(axis=1)].reset_index(drop=True)


def fit_pair(model, features, train, counts=None, counts_val_train=None):
    """The model on every training year, and on the years before VAL_YEAR with its alert level: the 99th
    percentile of its VAL_YEAR probabilities (weighted, since VAL_YEAR's training rows are a sample).
    A rate table ("official") is fitted on hourly_counts, the full table's counts, not on the sample."""
    params = PARAMS if model == "xgboost" else None
    val_train, val = train[train.year < VAL_YEAR], train[train.year == VAL_YEAR]
    if counts is not None:
        fitted = models.build(model, params).fit(counts[features], counts.y, sample_weight=counts.weight)
        early = models.build(model, params).fit(counts_val_train[features], counts_val_train.y,
                                                sample_weight=counts_val_train.weight)
    else:
        fitted = models.build(model, params).fit(train[features], train.y, sample_weight=train.weight)
        early = models.build(model, params).fit(val_train[features], val_train.y, sample_weight=val_train.weight)
    level = weighted_quantile(early.predict_proba(val[features])[:, 1], val.weight, 0.99)
    return fitted, level


def with_version(test, features, version):
    """The 2025 feature matrix with the window weather swapped for one version's."""
    x = test[features].copy()
    if version not in ("-", "actual"):
        cols = [c for c in WINDOW if c in features]           # a model on fewer window inputs (WINDOW_V1)
        x[cols] = test[[f"{c}|{version}" for c in cols]].to_numpy()
    return x


RUN_AGES = [2, 3, 4, 5, 6]               # the headline's five runs; forecast hours up to 6 + 2 + 5 = 13 (all stored)
RUN_NAMES = [f"run {k} h before" for k in RUN_AGES]


def five_runs(f):
    """The window weather from each of the five runs issued 2-6 hours before a decision (states_2025's versions)."""
    return {n: window_from_forecast(f, k) for n, k in zip(RUN_NAMES, RUN_AGES, strict=True)}


def five_run_mean(model, rows, features):
    """The headline's probability: the model fed each of the five runs in turn, averaged."""
    return np.mean([model.predict_proba(with_version(rows, features, n))[:, 1] for n in RUN_NAMES], axis=0)


def fit_versions(specs, train, counts, seeds=(0,), params=None):
    """specs: {label: (model, features)} -> {label: (fitted, features)}. XGBoost on the sampled training rows with
    their weights (params: the headline's settings unless given); a rate table ("official") on hourly_counts. More
    seeds add "<label>|seed<s>" entries."""
    params = PARAMS if params is None else params
    out = {}
    for label, (model, features) in specs.items():
        if model == "official":
            out[label] = (models.build("official").fit(counts[features], counts.y, sample_weight=counts.weight),
                          features)
            continue
        for s in seeds:
            fitted = models.build(model, params | {"random_state": s}).fit(train[features], train.y,
                                                                            sample_weight=train.weight)
            out[label if s == seeds[0] else f"{label}|seed{s}"] = (fitted, features)
        print(f"fitted {label}", flush=True)
    return out


def predict_five_runs(fitted, year=TEST_YEAR, add=None, require_actual=True):
    """Each fitted version's probability for every scored decision of `year`, a state at a time: the mean over the
    five runs for a model with window weather, its plain probability otherwise. add(rows) -> rows joins more
    columns onto each state's rows first (place inputs)."""
    parts = []
    for _, rows, _ in states_2025(five_runs, year=year, require_actual=require_actual):
        if add is not None:
            rows = add(rows)
        out = rows[["region_fips", "block_start", "y"]].copy()
        for label, (m, features) in fitted.items():
            out[label] = (five_run_mean(m, rows, features) if WINDOW[0] in features
                          else m.predict_proba(rows[features])[:, 1])
        parts.append(out)
        del rows
    return pd.concat(parts, ignore_index=True)


def official_counts():
    """The warnings + outlook rate table's counts over the full training table, and over the years before VAL_YEAR."""
    official = models.NEEDS_COLUMNS["official"]
    return (data.hourly_counts(THRESHOLD_PCT, TRAIN_YEARS, LEAD, official),
            data.hourly_counts(THRESHOLD_PCT, [y for y in TRAIN_YEARS if y < VAL_YEAR], LEAD, official))


def predict():
    """Every version's 2025 probabilities on the same decisions, and each one's alert level fixed on 2024."""
    train = train_rows()
    base = data.resolve_features(FEATURES)
    official = models.NEEDS_COLUMNS["official"]
    counts, counts_early = official_counts()
    specs, levels = [], {}
    for label, model, features, versions in (
        ("warnings + outlook", "official", official, ["-"]),
        ("forecast-ready", "xgboost", base, ["-"]),
        ("+ window weather", "xgboost", base + WINDOW, ["actual", "1 h fcst", "forecast"]),
    ):
        fitted, level = fit_pair(model, features, train, *((counts, counts_early) if model == "official" else ()))
        for version in versions:
            name = label if version == "-" else f"{label}: {version}"
            specs.append((name, fitted, features, version))
            levels[name] = level
        print(f"fitted {label}", flush=True)
    del train

    def versions(f):
        return {"1 h fcst": window_from_hourly(f[f.fhour == 1].drop(columns=["run", "fhour"])),
                "forecast": window_from_forecast(f)}

    parts = []
    for _, test, _ in states_2025(versions):
        out = test[["region_fips", "block_start", "y"]].copy()
        for name, fitted, features, version in specs:
            out[name] = fitted.predict_proba(with_version(test, features, version))[:, 1]
        parts.append(out)
        del test
    out = pd.concat(parts, ignore_index=True)
    out.to_parquet(PREDICTIONS, index=False)
    pd.Series(levels).to_json(PREDICTIONS.with_suffix(".levels.json"))
    return out, levels


def evaluate(pred, levels):
    """Scores with 95% storm-day ranges: PR-AUC, alerts at the frozen level, and alerts at one shared
    alert share (each version's own top EQUAL_SHARE of 2025 hours: no outcomes used), plus paired
    differences against the forecast-ready model and the official forecasts."""
    onsets = onset_hours(TEST_YEAR)
    first = storm_day(pd.Series([pd.Timestamp(f"{TEST_YEAR - 1}-12-31")]))[0]
    row_day = ((storm_day(pred.block_start) - first).dt.days).to_numpy()
    onset_day = ((storm_day(onsets.hour) - first).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(max(row_day.max(), onset_day.max()) + 1))
    names = list(levels)
    auc = {n: pr_auc_resamples(pred.y, pred[n], row_day, counts) for n in names}
    rows = []
    for n in names:
        p = pred[n].to_numpy()
        r = {"model": n, "onset_pr_auc": score(pred.y, p)["pr_auc"]}
        r["onset_pr_auc_lo"], r["onset_pr_auc_hi"] = interval(auc[n])
        for ref in ("forecast-ready", "warnings + outlook"):
            if n != ref:
                r[f"diff_vs_{ref}_lo"], r[f"diff_vs_{ref}_hi"] = interval(auc[n] - auc[ref])
                r[f"ratio_vs_{ref}_lo"], r[f"ratio_vs_{ref}_hi"] = interval(auc[n] / auc[ref])
        for kind, cut in (("frozen", levels[n]), ("equal_share", np.quantile(p, 1 - EQUAL_SHARE))):
            flagged = pd.Series(p > cut, index=pred.index)
            hit = np.array(caught_flags(pred, flagged, onsets, LEAD), dtype=float)
            r[f"{kind}_alert_share"] = flagged.mean()
            r[f"{kind}_precision"] = pred.y[flagged].mean()
            r[f"{kind}_precision_lo"], r[f"{kind}_precision_hi"] = interval(
                weighted_mean_resamples(pred.y[flagged], row_day[flagged.to_numpy()], counts))
            r[f"{kind}_caught"] = hit.mean()
            r[f"{kind}_caught_lo"], r[f"{kind}_caught_hi"] = interval(weighted_mean_resamples(hit, onset_day, counts))
            r[f"{kind}_episodes"] = episodes(pred, flagged)
        r["n_rows"], r["n_events"], r["n_onsets"] = len(pred), int(pred.y.sum()), len(onsets)
        rows.append(r)
        print({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()}, flush=True)
    pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / "forecast_test_2025.csv", index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-cache", action="store_true", help="reuse the saved predictions")
    args = parser.parse_args()
    if args.from_cache:
        pred = pd.read_parquet(PREDICTIONS)
        levels = pd.read_json(PREDICTIONS.with_suffix(".levels.json"), typ="series").to_dict()
    else:
        pred, levels = predict()
    evaluate(pred, levels)


if __name__ == "__main__":
    main()
