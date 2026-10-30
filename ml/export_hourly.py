"""Export the hourly (moving-window) results the site and dashboard read.

Nothing is trained here: it reads the 2025 predictions saved by ml/forecast_test.py and
ml/forecast_ensemble.py, and the results files, and writes small tables next to the ones
ml/export_app_data.py writes (regions, yearly history, state outlines stay as they are).

The headline model is "with HRRR forecasts, mean of 5 runs" (docs/experiments.md, E21): the
moving-window model fed the runs issued 2-6 h before each decision, 2 h ahead.

Writes data/app/:
  hourly_storms.parquet   the biggest 2025 storm days, every region-hour from 12 h before the peak to
                          18 h after: share of customers out, and each model's probability and range
                          (NaN when the region was already >= 5% out: nothing to predict)
  alert_curves.parquet    per model and alert share (the top x% of 2025 hours): new outages caught,
                          precision, alert episodes, and net dollars for each staging scenario
  county_hourly.parquet   per region, headline model: new outages, caught at the headline alert
                          share, expected (sum of probabilities) and actual new-outage hours
  ladder.parquet          each model's onset PR-AUC with its storm-day range, and paired ratios
  lead_time.parquet       moving_window_2025.csv: score and caught by lead, per model
  calibration.parquet     forecast_ensemble_bins_2025.csv: predicted vs observed by probability bin
  meta_hourly.json        the numbers the pages quote

Usage: pixi run python -m ml.export_hourly
"""
import json

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from ml import data
from ml.moving_window import THRESHOLD_PCT, caught_flags, episodes, onset_hours
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day
from ml.value import MIXES, RESTORATION_CUT, STAGING_COST
from ml.value_hourly import LEAD, avoidable, net_savings, outages

OUT = data.ROOT / "data" / "app"
CACHE = data.ROOT / "data" / "cache"
RESULTS = data.ROOT / "ml" / "results"
TEST_YEAR = 2025
HEADLINE = "With HRRR forecasts (mean of 5 runs)"
MODELS = {                                   # page label: column in the merged predictions
    "Warnings + outlook": "warnings + outlook",
    "No forecasts": "forecast-ready",
    "With HRRR forecasts (newest run)": "p_newest",
    HEADLINE: "p_mean",
    "Perfect weather (ceiling)": "+ window weather: actual",
}
HEADLINE_SHARE = 0.0075                      # the alert share the pages quote (E19)
SHARES = [0.001, 0.002, 0.003, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05]
N_STORMS = 8


def predictions():
    """Every model's 2025 probability on the decisions all of them scored."""
    a = pd.read_parquet(CACHE / "forecast_test_2025_predictions.parquet")
    b = pd.read_parquet(CACHE / "forecast_ensemble_2025.parquet").drop(columns="y")
    return a.merge(b, on=["region_fips", "block_start"], how="inner")


def alert_curves(pred, onsets):
    events = outages([TEST_YEAR]).reset_index(drop=True)
    mix = MIXES["typical mix"]
    saved = {(cut, cost): avoidable(events, mix, cut) for cut in RESTORATION_CUT for cost in STAGING_COST}
    rows = []
    for label, col in MODELS.items():
        p = pred[col].to_numpy()
        for share in SHARES:
            flagged = pd.Series(p > np.quantile(p, 1 - share), index=pred.index)
            r = {"model": label, "alert_share": share, "actual_share": flagged.mean(),
                 "caught": np.mean(caught_flags(pred, flagged, onsets, LEAD)),
                 "precision": pred.y[flagged].mean(), "episodes": episodes(pred, flagged)}
            for (cut, cost), s in saved.items():
                r[f"net_cut{int(cut * 100)}_cost{cost // 1000}k"] = net_savings(pred, flagged, events, s, cost)[0]
            rows.append(r)
        print(label, flush=True)
    return pd.DataFrame(rows)


def county(pred, onsets):
    p = pred[MODELS[HEADLINE]]
    flagged = pd.Series(p > np.quantile(p, 1 - HEADLINE_SHARE), index=pred.index)
    on = onsets.assign(caught=caught_flags(pred, flagged, onsets, LEAD))
    by = on.groupby("region_fips").agg(new_outages=("caught", "size"), caught=("caught", "sum"))
    rows = pred.assign(p=p).groupby("region_fips").agg(expected=("p", "sum"), actual=("y", "sum"),
                                                       mean_probability=("p", "mean"))
    out = rows.join(by, how="left").fillna({"new_outages": 0, "caught": 0}).reset_index()
    out["caught_share"] = out.caught / out.new_outages.where(out.new_outages > 0)
    return out


def storms(pred):
    """The N_STORMS biggest storm days by customers out at the worst hour, ±hours around each peak."""
    con = duckdb.connect(str(data.DB), read_only=True)
    hours = con.sql(f"""
        SELECT region_fips, hour, pct_out, customers, pct_out * customers / 100 AS out
        FROM marts.mart_study__region_1h WHERE year(hour) = {TEST_YEAR}
    """).df()
    con.close()
    total = hours.groupby("hour").out.sum()
    day = (total.index - pd.Timedelta(hours=12)).floor("D")
    peaks = total.groupby(day).idxmax()
    top = total.loc[peaks].sort_values(ascending=False).head(N_STORMS).index
    keep = ["region_fips", "block_start"] + [c for c in ("p_mean", "p_low", "p_high", "p_newest",
                                                       "forecast-ready", "warnings + outlook") if c in pred]
    parts = []
    for i, peak in enumerate(sorted(top)):
        window = hours[hours.hour.between(peak - pd.Timedelta(hours=12), peak + pd.Timedelta(hours=18))]
        # a decision at h is about h + LEAD ... h + LEAD + 5: show it at the window's first hour
        p = pred[keep].assign(hour=pred.block_start + pd.Timedelta(hours=LEAD)).drop(columns="block_start")
        w = window.merge(p, on=["region_fips", "hour"], how="left")
        w["storm"], w["peak"], w["customers_out_peak"] = i, peak, total.loc[peak]
        parts.append(w)
    return pd.concat(parts, ignore_index=True)


def ladder(pred):
    """Each model's onset PR-AUC with a 95% storm-day range, and paired ratios against warnings + outlook
    and against the model without forecasts, all on the same decisions (ml/uncertainty.py)."""
    first = pd.Timestamp(f"{TEST_YEAR - 1}-12-31")
    day = (storm_day(pred.block_start) - first).dt.days.to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    auc = {label: pr_auc_resamples(pred.y, pred[col], day, counts) for label, col in MODELS.items()}
    rows = []
    for label, col in MODELS.items():
        r = {"model": label, "onset_pr_auc": average_precision_score(pred.y, pred[col])}
        r["lo"], r["hi"] = interval(auc[label])
        for ref, key in (("Warnings + outlook", "official"), ("No forecasts", "no_forecasts")):
            ratio = auc[label] / auc[ref]
            r[f"ratio_vs_{key}"] = r["onset_pr_auc"] / average_precision_score(pred.y, pred[MODELS[ref]])
            r[f"ratio_vs_{key}_lo"], r[f"ratio_vs_{key}_hi"] = interval(ratio)
            r[f"better_vs_{key}"] = float((ratio > 1).mean())        # share of resamples where this one wins
        rows.append(r)
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()}, flush=True)
    return pd.DataFrame(rows)


def main():
    pred = predictions()
    onsets = onset_hours(TEST_YEAR)
    print(f"{len(pred):,} decisions, {len(onsets):,} new outages", flush=True)
    curves = alert_curves(pred, onsets)
    curves.to_parquet(OUT / "alert_curves.parquet", index=False)
    county(pred, onsets).to_parquet(OUT / "county_hourly.parquet", index=False)
    storms(pred).to_parquet(OUT / "hourly_storms.parquet", index=False)
    lad = ladder(pred)
    lad.to_parquet(OUT / "ladder.parquet", index=False)
    pd.read_csv(RESULTS / "moving_window_2025.csv").to_parquet(OUT / "lead_time.parquet", index=False)
    pd.read_csv(RESULTS / "forecast_ensemble_bins_2025.csv").assign(bin=lambda d: d.bin.astype(str)) \
        .to_parquet(OUT / "calibration.parquet", index=False)

    at = curves[curves.alert_share == HEADLINE_SHARE].set_index("model")
    value = pd.read_csv(RESULTS / "value_hourly_2025.csv")
    value = value[value["mix"] == "typical mix"]
    meta = {
        "test_year": TEST_YEAR, "lead_hours": LEAD, "threshold_pct": THRESHOLD_PCT,
        "headline_model": HEADLINE, "headline_share": HEADLINE_SHARE,
        "n_decisions": len(pred), "n_new_outages": len(onsets), "event_rate": float(pred.y.mean()),
        "ladder": lad.set_index("model").to_dict(orient="index"),
        "at_headline_share": at[["caught", "precision", "episodes"]].to_dict(orient="index"),
        "value_no_forecasts": {"low": float(value.model.min()), "high": float(value.model.max()),
                               "official_low": float(value.official.min()),
                               "official_high": float(value.official.max())},
    }
    (OUT / "meta_hourly.json").write_text(json.dumps(meta, indent=2, default=float))
    print(json.dumps(meta, indent=2, default=float)[:3000])


if __name__ == "__main__":
    main()
