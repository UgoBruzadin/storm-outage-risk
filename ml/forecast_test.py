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

import duckdb
import numpy as np
import pandas as pd

from ml import data, models
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT, caught_flags, episodes, onset_hours
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day, weighted_mean_resamples

LEAD = 2
RUN_AGE = 2                                   # hours between a run's issue time and the decision
TRAIN_YEARS, VAL_YEAR, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2024, 2025
EQUAL_SHARE = 0.0075                          # the forecast-ready model's alert share at its frozen level
FCST_DIR = data.ROOT / "data" / "raw" / "weather" / "hrrr_fcst"
PREDICTIONS = data.ROOT / "data" / "cache" / "forecast_test_2025_predictions.parquet"
HOURLY = ["gust_ms", "wind10_ms", "wind850_ms", "shear_ms", "cape_jkg", "precip_mm", "temp_c",
          "freezing_level_m", "icing", "hail"]
WINDOW = ["win_gust_max_ms", "win_wind10_max_ms", "win_wind850_max_ms", "win_shear_0_6km_max_ms",
          "win_cape_max_jkg", "win_precip_sum_mm", "win_precip_max_1h_mm", "win_temp_min_c", "win_temp_mean_c",
          "win_freezing_level_min_m", "win_icing_hours", "win_hail_hours",
          "win_wind_x_precip", "win_wind_squared", "win_shear_x_cape"]


def prepare(hw):
    """Per-hour inputs to the 6-hour summaries, as in mart_study__region_1h."""
    hw = hw.copy()
    hw.loc[hw.precip_mm > 100, "precip_mm"] = np.nan                  # archive artifact (E14)
    hw["shear_ms"] = np.hypot(hw.u500 - hw.u10, hw.v500 - hw.v10)
    hw["icing"] = ((hw.temp_c <= 0) & (hw.precip_mm > 0)).astype(float)
    hw["hail"] = ((hw.cape_jkg >= 500) & (hw.precip_mm >= 2) & (hw.freezing_level_m <= 3500)).astype(float)
    hw.loc[hw.gust_ms.isna(), ["icing", "hail"]] = np.nan
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
    })
    out.loc[g["gust_ms"].count() < 6] = np.nan                           # all 6 hours or unknown
    out["win_wind_x_precip"] = out.win_gust_max_ms * out.win_precip_sum_mm
    out["win_wind_squared"] = out.win_gust_max_ms ** 2
    out["win_shear_x_cape"] = out.win_shear_0_6km_max_ms * out.win_cape_max_jkg
    return out


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


def actual_hourly(years):
    con = duckdb.connect(str(data.DB), read_only=True)
    hw = con.sql(f"""
        SELECT region_fips, hour, gust_ms, wind10_ms, wind850_ms, cape_jkg, precip_mm, temp_c,
               freezing_level_m, u10, v10, u500, v500
        FROM staging.stg_hrrr__hourly
        WHERE year(hour) BETWEEN {min(years)} AND {max(years) + 1}
    """).df()
    con.close()
    return hw


def forecasts(start, end):
    days = pd.date_range(start, end, freq="D")
    f = pd.concat([pd.read_parquet(FCST_DIR / f"{d:%Y%m%d}.parquet") for d in days], ignore_index=True)
    f["wind10_ms"] = np.hypot(f.u10, f.v10)
    f["wind850_ms"] = np.hypot(f.u850, f.v850)
    return f


def window_from_forecast(f, run_age=RUN_AGE):
    """For each decision hour h: the run issued run_age hours before h, forecast hours for h + LEAD ... + 5."""
    first = run_age + LEAD
    f = prepare(f[f.fhour.between(first, first + 5)])
    s = summarize(f.groupby(["region_fips", "run"]))
    s = s.reset_index()
    s["block_start"] = s.pop("run") + pd.Timedelta(hours=run_age)
    return s


def tables(versions):
    """Train, validation and 2025 rows, with actual window weather, and each version's window weather in
    the 2025 rows as `<feature>|<version>`; only 2025 decisions that every version has are kept.
    versions: {name: window table} from window_from_hourly / window_from_forecast."""
    df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR], LEAD)
    df["region_fips"] = df.region_fips.astype(str)
    print("actual weather windows", flush=True)
    actual = window_from_hourly(actual_hourly(TRAIN_YEARS + [TEST_YEAR]))
    df = df.merge(actual, on=["region_fips", "block_start"], how="left")
    train, val_train = df[df.year.isin(TRAIN_YEARS)], df[df.year < VAL_YEAR]
    val, test = df[df.year == VAL_YEAR], df[df.year == TEST_YEAR].copy()
    for name, w in versions.items():
        test = test.merge(w.rename(columns={c: f"{c}|{name}" for c in WINDOW}),
                          on=["region_fips", "block_start"], how="left")
    keep = test[[f"win_gust_max_ms|{n}" for n in versions] + ["win_gust_max_ms"]].notna().all(axis=1)
    print(f"2025 decisions with every version: {keep.sum():,} of {len(test):,}", flush=True)
    return train, val_train, val, test[keep]


def with_version(test, features, version):
    """The 2025 feature matrix with the window weather swapped for one version's."""
    x = test[features].copy()
    if version not in ("-", "actual"):
        x[WINDOW] = test[[f"{c}|{version}" for c in WINDOW]].to_numpy()
    return x


def predict():
    """Every version's 2025 probabilities on the same decisions, and each one's alert level fixed on 2024."""
    f = forecasts(f"{TEST_YEAR - 1}-12-31", f"{TEST_YEAR}-12-31")
    train, val_train, val, test = tables({
        "1 h fcst": window_from_hourly(f[f.fhour == 1].drop(columns=["run", "fhour"])),
        "forecast": window_from_forecast(f)})
    base = data.resolve_features(FEATURES)
    official = models.NEEDS_COLUMNS["official"]

    out = test[["region_fips", "block_start", "y"]].copy()
    levels = {}
    for label, model, features, versions in (
        ("warnings + outlook", "official", official, ["-"]),
        ("forecast-ready", "xgboost", base, ["-"]),
        ("+ window weather", "xgboost", base + WINDOW, ["actual", "1 h fcst", "forecast"]),
    ):
        params = PARAMS if model == "xgboost" else None
        fitted = models.build(model, params).fit(train[features], train["y"])
        level = pd.Series(models.build(model, params).fit(val_train[features], val_train["y"])
                          .predict_proba(val[features])[:, 1]).quantile(0.99)
        for version in versions:
            name = label if version == "-" else f"{label}: {version}"
            out[name], levels[name] = fitted.predict_proba(with_version(test, features, version))[:, 1], level
            print(name, flush=True)
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
