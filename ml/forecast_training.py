"""Training on forecasts, and county-wide forecast summaries (docs/experiments.md, E40-E42).

The headline model learns from the weather that actually happened and is fed forecasts at test time (E19, E21).
With the HRRR forecast archive for 2020-2025 summarized over each county's whole area
(ingest/fetch_hrrr_forecast_area.py), this tests:

  E40  training on forecasts: the window's weather from the run issued RUN_AGE hours before each decision, for
       training and test alike, against the current model (trained on actual weather) on the same rows
  E41  + county-wide summaries: the window's strongest gust anywhere in the county, the share above storm
       thresholds, simulated radar, storm-column ice (VIL) and lightning
  E42  the better of the two tested on 2022, 2023, 2024 and 2025 (trained on 2020 to the year before), against
       warnings + outlook; and its calibration on 2025

All on fresh new outages, 2 hours ahead. 2025 is also scored with the mean over the runs issued 2-6 hours before
(runs before December 2020 forecast only 9 hours, so the five-run mean exists for later years only; training uses
the newest run, which every year has).

Usage: pixi run python -m ml.forecast_training
Writes ml/results/forecast_training_2025.csv, forecast_training_years.csv, forecast_training_calibration_2025.csv.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap

from ml import data, models
from ml import forecast_test as ft
from ml.forecast_ensemble import BINS
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT

AREA_DIR = data.ROOT / "data" / "raw" / "weather" / "hrrr_fcst_area"
RESULTS = data.ROOT / "ml" / "results"
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
LEAD, NEWEST, AGES = 2, 2, [2, 3, 4, 5, 6]
AREA_COLS = ["area_gust_max", "area_gust_share20", "area_wind1h_max", "area_wind1h_share18", "area_cape_max",
             "area_precip_max", "area_precip_share10", "area_refc_max", "area_refc_share45", "area_vil_max",
             "area_ltng_max", "area_ltng_share"]
AREA_WINDOW = [f"win_{c}" for c in AREA_COLS]


def windows(run_ages, years):
    """Per decision (region, hour): the window's weather from the run issued `age` hours before it, point summaries
    (as forecast_test.py) and the maximum of each county-wide summary over the window, reduced day by day."""
    parts = {age: [] for age in run_ages}
    days = pd.date_range(f"{min(years) - 1}-12-31", f"{max(years)}-12-31", freq="D")
    for i, day in enumerate(days):
        path = AREA_DIR / f"{day:%Y%m%d}.parquet"
        if not path.exists():
            continue
        f = pd.read_parquet(path)
        f["wind10_ms"], f["wind850_ms"] = np.hypot(f.u10, f.v10), np.hypot(f.u850, f.v850)
        for age in run_ages:
            first = age + LEAD
            g = f[f.fhour.between(first, first + 5)]
            point = ft.window_from_forecast(g, age)
            area = g.groupby(["region_fips", "run"])[AREA_COLS].max().reset_index()
            area.columns = ["region_fips", "run"] + AREA_WINDOW
            area["block_start"] = area.pop("run") + pd.Timedelta(hours=age)
            w = point.merge(area, on=["region_fips", "block_start"], how="left")
            parts[age].append(w.astype({c: "float32" for c in ft.WINDOW + AREA_WINDOW}))
        if i % 100 == 0:
            print(f"windows: {day:%Y-%m-%d}", flush=True)
    return {age: pd.concat(p, ignore_index=True) for age, p in parts.items() if p}


def main():
    df = data.load_hourly(THRESHOLD_PCT, YEARS, LEAD)
    df["region_fips"] = df.region_fips.astype(str)
    actual = ft.window_from_hourly(ft.actual_hourly(YEARS))
    w = windows(AGES, YEARS)
    newest = w[NEWEST]
    base = data.resolve_features(FEATURES)
    cols = models.NEEDS_COLUMNS["official"]

    # rows every version has: the newest run's window exists, and the actual weather for the trained-on-actual model
    df = df.merge(newest.rename(columns={c: f"{c}|fc" for c in ft.WINDOW}), on=["region_fips", "block_start"],
                  how="inner")
    df = df.merge(actual, on=["region_fips", "block_start"], how="left").dropna(subset=["win_gust_max_ms|fc"])
    for c in ft.WINDOW:                        # forecast features under the names the model uses
        df[f"{c}|actual"] = df[c]
    train, test = df[df.year < 2025], df[df.year == 2025].copy()
    print(f"train {len(train):,} rows, test {len(test):,}", flush=True)

    def use(frame, source):
        x = frame.copy()
        x[ft.WINDOW] = frame[[f"{c}|{source}" for c in ft.WINDOW]].to_numpy()
        return x

    def mean_over_runs(fitted, features):
        """2025 probabilities averaged over the runs issued 2-6 hours before (where all five exist)."""
        t = test[["region_fips", "block_start", *[c for c in features if c not in ft.WINDOW + AREA_WINDOW]]]
        probs = []
        for age in AGES:
            a = w[age]
            a = a[a.block_start.dt.year == 2025]
            x = t.merge(a, on=["region_fips", "block_start"], how="left")
            probs.append(fitted.predict_proba(x[features])[:, 1])
        probs = np.column_stack(probs)
        ok = ~np.isnan(probs).any(axis=1)
        return probs.mean(axis=1), ok

    official = models.build("official").fit(train[cols], train["y"]).predict_proba(test[cols])[:, 1]
    runs = {
        "trained on actual weather, fed forecasts (current)": (base + ft.WINDOW, "actual"),
        "trained on forecasts": (base + ft.WINDOW, "fc"),
        "trained on forecasts + county-wide summaries": (base + ft.WINDOW + AREA_WINDOW, "fc"),
    }
    rows, best, best_score = [], None, -1
    for label, (features, source) in runs.items():
        fitted = models.build("xgboost", PARAMS).fit(use(train, source)[features], train["y"])
        p = fitted.predict_proba(use(test, "fc")[features])[:, 1]
        pm, ok = mean_over_runs(fitted, features)
        row = {"model": label, "pr_auc_newest_run": ap(test.y, p), "pr_auc_official": ap(test.y, official),
               "ratio_newest": ap(test.y, p) / ap(test.y, official),
               "pr_auc_mean_of_runs": ap(test.y[ok], pm[ok]), "pr_auc_official_same_rows": ap(test.y[ok], official[ok]),
               "rows_with_all_runs": int(ok.sum()), "rows": len(test)}
        rows.append(row)
        print(row, flush=True)
        if label != list(runs)[0] and row["pr_auc_newest_run"] > best_score:
            best, best_score = (label, features, source, fitted, p), row["pr_auc_newest_run"]
    pd.DataFrame(rows).to_csv(RESULTS / "forecast_training_2025.csv", index=False)

    # E42: the better version on four test years, and its calibration on 2025
    label, features, source, fitted, p = best
    calib = pd.DataFrame({"y": test.y.to_numpy(), "p": p, "bin": pd.cut(p, BINS, include_lowest=True)})
    calib.groupby("bin", observed=True).agg(decisions=("y", "size"), predicted=("p", "mean"), observed=("y", "mean")) \
         .to_csv(RESULTS / "forecast_training_calibration_2025.csv")
    yrows = []
    for year in (2022, 2023, 2024, 2025):
        tr, te = df[df.year < year], df[df.year == year]
        m = models.build("xgboost", PARAMS).fit(use(tr, source)[features], tr["y"])
        pm_ = m.predict_proba(use(te, "fc")[features])[:, 1]
        o = models.build("official").fit(tr[cols], tr["y"]).predict_proba(te[cols])[:, 1]
        yrows.append({"model": label, "test_year": year, "train_years": f"2020-{year - 1}",
                      "positive_windows": int(te.y.sum()), "pr_auc_model": ap(te.y, pm_),
                      "pr_auc_official": ap(te.y, o), "ratio": ap(te.y, pm_) / ap(te.y, o)})
        print(yrows[-1], flush=True)
    pd.DataFrame(yrows).to_csv(RESULTS / "forecast_training_years.csv", index=False)


if __name__ == "__main__":
    main()
