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

# HRRR runs as issued with county-wide summaries for every county (ingest/fetch_hrrr_grib.py --area, the same columns
# as the MO + IL zarr extract ingest/fetch_hrrr_forecast_area.py wrote to hrrr_fcst_area)
AREA_DIR = data.ROOT / "data" / "raw" / "weather" / "hrrr_grib_area"
RESULTS = data.ROOT / "ml" / "results"
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
LEAD, NEWEST, AGES = 2, 2, [2, 3, 4, 5, 6]
AREA_COLS = ["area_gust_max", "area_gust_share20", "area_wind1h_max", "area_wind1h_share18", "area_cape_max",
             "area_precip_max", "area_precip_share10", "area_refc_max", "area_refc_share45", "area_vil_max",
             "area_ltng_max", "area_ltng_share"]
AREA_WINDOW = [f"win_{c}" for c in AREA_COLS]
FC = {c: f"{c}|fc" for c in ft.WINDOW}           # the newest run's point summaries, beside the actual weather's


def window_of(f, age):
    """Per decision (region, hour): the window's weather from the run issued `age` hours before it, point summaries
    (as forecast_test.py) and the maximum of each county-wide summary over the window."""
    first = age + LEAD
    g = f[f.fhour.between(first, first + 5)]
    point = ft.window_from_forecast(g, age)
    area = g.groupby(["region_fips", "run"])[AREA_COLS].max().reset_index()
    area.columns = ["region_fips", "run"] + AREA_WINDOW
    area["block_start"] = area.pop("run") + pd.Timedelta(hours=age)
    return point.merge(area, on=["region_fips", "block_start"], how="left") \
                .astype({c: "float32" for c in ft.WINDOW + AREA_WINDOW})


def windows(year, age, states=None):
    """window_of() for every decision of `year`, built a state at a time from the daily files split by state, cached
    for the whole country per year and run age (data.cached) and read back for `states`."""
    def build():
        parts = []
        for s in data.warehouse_states():
            f = ft.forecasts(f"{year - 1}-12-31", f"{year}-12-31", states=[s], source=AREA_DIR)
            if len(f):
                w = window_of(f, age)
                parts.append(w[w.block_start.dt.year == year].assign(state=s))
            del f
        return pd.concat(parts, ignore_index=True)
    w = data.cached("area_window", {"year": year, "age": age, "lead": LEAD}, build,
                    code_files=(data.__file__, ft.__file__, __file__),
                    filters=[("state", "in", list(states))] if states else None)
    return w.drop(columns="state")


def add_windows(df, year):
    """One year's decisions + the actual window weather + the newest run's as `<feature>|fc` and its county-wide
    summaries; only decisions the newest run covers (data.sampled_years' `add`)."""
    df = ft.add_actual_window(df, year)
    newest = windows(year, NEWEST).rename(columns=FC)
    df = df.merge(newest, on=["region_fips", "block_start"], how="inner").dropna(subset=["win_gust_max_ms|fc"])
    for c in ft.WINDOW:                        # the actual weather under the names the model uses
        df[f"{c}|actual"] = df[c]
    return df


def use(frame, source):
    """The rows with the window weather swapped for `source`'s (actual or fc)."""
    x = frame.copy()
    x[ft.WINDOW] = frame[[f"{c}|{source}" for c in ft.WINDOW]].to_numpy()
    return x


def test_rows(year):
    """Every scored decision of `year`, a state at a time, with the windows add_windows() gives training rows."""
    for s, rows in data.state_rows(THRESHOLD_PCT, year, LEAD):
        rows = ft.add_actual_window(rows, year)
        newest = windows(year, NEWEST, states=[s]).rename(columns=FC)
        rows = rows.merge(newest, on=["region_fips", "block_start"], how="inner").dropna(
            subset=["win_gust_max_ms|fc"])
        for c in ft.WINDOW:
            rows[f"{c}|actual"] = rows[c]
        yield s, rows


def fit(train, features, source):
    return models.build("xgboost", PARAMS).fit(use(train, source)[features], train.y, sample_weight=train.weight)


def main():
    """Training rows sampled a year at a time (data.sampled_years), the warnings + outlook rate table on the full
    table's counts, every test year scored a state at a time."""
    base = data.resolve_features(FEATURES)
    cols = models.NEEDS_COLUMNS["official"]
    runs = {
        "trained on actual weather, fed forecasts (current)": (base + ft.WINDOW, "actual"),
        "trained on forecasts": (base + ft.WINDOW, "fc"),
        "trained on forecasts + county-wide summaries": (base + ft.WINDOW + AREA_WINDOW, "fc"),
    }
    train = data.sampled_years(THRESHOLD_PCT, YEARS[:-1], LEAD, add=add_windows)
    fitted = {label: fit(train, f, s) for label, (f, s) in runs.items()}
    del train
    c = data.hourly_counts(THRESHOLD_PCT, YEARS[:-1], LEAD, cols)
    official = models.build("official").fit(c[cols], c.y, sample_weight=c.weight)

    # 2025, a state at a time: the newest run, and the mean over the five runs where all five exist
    y, off, newest = [], [], {k: [] for k in runs}
    mean_runs, ok = {k: [] for k in runs}, []
    for s, test in test_rows(2025):
        y.append(test.y.to_numpy())
        off.append(official.predict_proba(test[cols])[:, 1])
        fc = use(test, "fc")
        for label, (features, _) in runs.items():
            newest[label].append(fitted[label].predict_proba(fc[features])[:, 1])
        point = test[["region_fips", "block_start", *[c for c in base if c not in ft.WINDOW + AREA_WINDOW]]]
        probs, have = {label: [] for label in runs}, []
        for age in AGES:
            x = point.merge(windows(2025, age, states=[s]), on=["region_fips", "block_start"], how="left")
            have.append(x[ft.WINDOW[0]].notna().to_numpy())
            for label, (features, _) in runs.items():
                probs[label].append(fitted[label].predict_proba(x[features])[:, 1])
        for label in runs:
            mean_runs[label].append(np.column_stack(probs[label]).mean(axis=1))
        # all five runs' windows exist (XGBoost scores a missing window as missing, never as NaN, so the
        # probabilities can't tell; MO + IL's E40-E42 checked the probabilities, which kept every row)
        ok.append(np.column_stack(have).all(axis=1))
        del test, fc, point
    y, off, ok = np.concatenate(y), np.concatenate(off), np.concatenate(ok)
    rows, best, best_score = [], None, -1
    for label, (features, source) in runs.items():
        p, pm = np.concatenate(newest[label]), np.concatenate(mean_runs[label])
        row = {"model": label, "pr_auc_newest_run": ap(y, p), "pr_auc_official": ap(y, off),
               "ratio_newest": ap(y, p) / ap(y, off),
               "pr_auc_mean_of_runs": ap(y[ok], pm[ok]), "pr_auc_official_same_rows": ap(y[ok], off[ok]),
               "rows_with_all_runs": int(ok.sum()), "rows": len(y)}
        rows.append(row)
        print(row, flush=True)
        if label != list(runs)[0] and row["pr_auc_newest_run"] > best_score:
            best, best_score = (label, features, source, p), row["pr_auc_newest_run"]
    pd.DataFrame(rows).to_csv(RESULTS / "forecast_training_2025.csv", index=False)

    # E42: the better version on four test years, and its calibration on 2025
    label, features, source, p = best
    calib = pd.DataFrame({"y": y, "p": p, "bin": pd.cut(p, BINS, include_lowest=True)})
    calib.groupby("bin", observed=True).agg(decisions=("y", "size"), predicted=("p", "mean"), observed=("y", "mean")) \
         .to_csv(RESULTS / "forecast_training_calibration_2025.csv")
    yrows = []
    for year in (2022, 2023, 2024, 2025):
        years = list(range(YEARS[0], year))
        tr = data.sampled_years(THRESHOLD_PCT, years, LEAD, add=add_windows)
        m = fit(tr, features, source)
        del tr
        c = data.hourly_counts(THRESHOLD_PCT, years, LEAD, cols)
        o_model = models.build("official").fit(c[cols], c.y, sample_weight=c.weight)
        ys, pm_, o = [], [], []
        for _, te in test_rows(year):
            ys.append(te.y.to_numpy())
            pm_.append(m.predict_proba(use(te, "fc")[features])[:, 1])
            o.append(o_model.predict_proba(te[cols])[:, 1])
            del te
        ys, pm_, o = np.concatenate(ys), np.concatenate(pm_), np.concatenate(o)
        yrows.append({"model": label, "test_year": year, "train_years": f"2020-{year - 1}",
                      "positive_windows": int(ys.sum()), "pr_auc_model": ap(ys, pm_),
                      "pr_auc_official": ap(ys, o), "ratio": ap(ys, pm_) / ap(ys, o)})
        print(yrows[-1], flush=True)
    pd.DataFrame(yrows).to_csv(RESULTS / "forecast_training_years.csv", index=False)


if __name__ == "__main__":
    main()
