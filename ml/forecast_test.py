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

Training on actual weather and scoring on forecasts understates a model trained on forecasts,
which would learn how far to trust them; this cheap version needs forecasts for 2025 only.
The alert level is fixed on 2024 (trained 2020-2023, actual weather), as in moving_window.py.

Usage: pixi run python -m ml.forecast_test
Writes ml/results/forecast_test_2025.csv. Needs ingest/fetch_hrrr_forecast.py for 2024-12-31 .. 2025-12-31.
"""
import duckdb
import numpy as np
import pandas as pd

from ml import data, models
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT, caught, episodes, onset_hours

LEAD = 2
RUN_AGE = 2                                   # hours between a run's issue time and the decision
TRAIN_YEARS, VAL_YEAR, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2024, 2025
FCST_DIR = data.ROOT / "data" / "raw" / "weather" / "hrrr_fcst"
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


def forecasts():
    f = pd.concat([pd.read_parquet(p) for p in sorted(FCST_DIR.glob("*.parquet"))], ignore_index=True)
    f["wind10_ms"] = np.hypot(f.u10, f.v10)
    f["wind850_ms"] = np.hypot(f.u850, f.v850)
    return f


def window_from_forecast(f):
    """For each decision hour h: the run issued RUN_AGE hours before h, forecast hours for h + LEAD ... + 5."""
    first = RUN_AGE + LEAD
    f = prepare(f[f.fhour.between(first, first + 5)])
    s = summarize(f.groupby(["region_fips", "run"]))
    s = s.reset_index()
    s["block_start"] = s.pop("run") + pd.Timedelta(hours=RUN_AGE)
    return s


def main():
    df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR], LEAD)
    df["region_fips"] = df.region_fips.astype(str)
    print("actual weather windows", flush=True)
    actual = window_from_hourly(actual_hourly(TRAIN_YEARS + [TEST_YEAR]))
    df = df.merge(actual, on=["region_fips", "block_start"], how="left")
    f = forecasts()
    one_h = window_from_hourly(f[f.fhour == 1].drop(columns=["run", "fhour"]))
    issued = window_from_forecast(f)

    base = data.resolve_features(FEATURES)
    with_window = base + WINDOW
    train, val_train = df[df.year.isin(TRAIN_YEARS)], df[df.year < VAL_YEAR]
    val, test = df[df.year == VAL_YEAR], df[df.year == TEST_YEAR].copy()
    # score only the decisions every version has, so the rows match
    for name, w in (("1 h fcst", one_h), ("forecast", issued)):
        test = test.merge(w.rename(columns={c: f"{c}|{name}" for c in WINDOW}),
                          on=["region_fips", "block_start"], how="left")
    keep = test[[f"win_gust_max_ms|{n}" for n in ("1 h fcst", "forecast")] + ["win_gust_max_ms"]].notna().all(axis=1)
    print(f"2025 decisions with every version: {keep.sum():,} of {len(test):,}", flush=True)
    test = test[keep]
    onsets = onset_hours(TEST_YEAR)

    rows = []
    for label, features in (("forecast-ready (no window weather)", base), ("+ window weather", with_window)):
        fitted = models.build("xgboost", PARAMS).fit(train[features], train["y"])
        level = pd.Series(models.build("xgboost", PARAMS).fit(val_train[features], val_train["y"])
                          .predict_proba(val[features])[:, 1]).quantile(0.99)
        versions = ["actual"] if features is base else ["actual", "1 h fcst", "forecast"]
        for version in versions:
            x = test[features].copy()
            if version != "actual":
                x[WINDOW] = test[[f"{c}|{version}" for c in WINDOW]].to_numpy()
            p = fitted.predict_proba(x)[:, 1]
            flagged = pd.Series(p > level, index=test.index)
            s = score(test["y"].to_numpy(), p)
            rows.append({"model": label, "window_weather": version if features is not base else "-",
                         "onset_pr_auc": s["pr_auc"], "alert_share": flagged.mean(),
                         "alert_precision": test.loc[flagged, "y"].mean(),
                         "caught": caught(test, flagged, onsets, LEAD), "alert_episodes": episodes(test, flagged),
                         "n_rows": len(test), "n_events": int(test["y"].sum())})
            print({k: round(v, 4) if isinstance(v, float) else v for k, v in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / "forecast_test_2025.csv", index=False)


if __name__ == "__main__":
    main()
