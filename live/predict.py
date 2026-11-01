"""One hour of the live forecast: fetch the feeds, build the inputs, score every county.

For the decision hour h (the current hour, UTC): the chance of a new outage of >= 5% of customers in the 6 hours
starting at h + 2, from the frozen model (live/model) fed each HRRR run issued 2-6 hours before h; the forecast is
their mean, the range their lowest and highest. Runs not yet in the archive are left out (n_runs says how many
were used).

Writes, under --out (default live/out), one file per decision hour so a re-run replaces only its own hour:
  predictions/<YYYY>/<MM>/<DD>/<HH>.parquet   one row per county
  inputs/<YYYY>/<MM>/<DD>/<HH>.csv.gz         with --inputs: the inputs behind them, for the feed parity check during
                                              the shakedown (afterwards they can be rebuilt from the public archives)
  latest.json                                 the newest hour, for the story page and the dashboard

Usage: pixi run python -m live.predict [--hour 2026-11-01T18] [--out live/out] [--inputs]
"""
import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from live import features as lf
from live import sources

MODEL = Path(__file__).parent / "model"


def save(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values("region_fips").to_parquet(path, index=False, compression="zstd")


def run(hour, out, keep_inputs=False):
    meta = json.loads((MODEL / "meta.json").read_text())
    model = XGBClassifier()
    model.load_model(MODEL / "model.json")
    regions = pd.read_parquet(lf.STATIC / "regions.parquet")
    started = datetime.now(UTC)

    hw = lf.hourly_weather(sources.weather(regions))
    warn = sources.warnings(hour - pd.Timedelta(days=3), hour)
    table = lf.outlook_table(sources.outlooks(hour - pd.Timedelta(days=2), hour), regions)
    runs = [hour - pd.Timedelta(hours=a) for a in meta["run_ages"]]
    fc = sources.forecasts(regions, runs)
    rows = lf.model_rows(hw, warn, table, [hour], fc, run_ages=meta["run_ages"])

    features = meta["features"]
    base = [c for c in features if not c.startswith("win_")]
    probs = {}
    for age in meta["run_ages"]:
        cols = [f"{c}|{age}" for c in features if c.startswith("win_")]
        if cols[0] not in rows or rows[cols[0]].isna().all():
            continue
        x = rows[base].copy()
        x[[c for c in features if c.startswith("win_")]] = rows[cols].to_numpy()
        probs[age] = model.predict_proba(x[features])[:, 1]
    if not probs:
        raise RuntimeError(f"no HRRR run issued 2-6 hours before {hour} is in the archive yet")
    p = np.column_stack(list(probs.values()))

    level = meta["alert_level"]
    pred = pd.DataFrame({
        "decision_hour": hour, "region_fips": rows.region_fips,
        "window_start": hour + pd.Timedelta(hours=meta["lead_hours"]),
        "window_end": hour + pd.Timedelta(hours=meta["lead_hours"] + 6),
        "p_mean": p.mean(axis=1), "p_low": p.min(axis=1), "p_high": p.max(axis=1), "n_runs": p.shape[1],
        "has_weather": rows.has_weather.to_numpy(),
    })
    pred["alert"] = pred.p_mean >= level
    pred["model_trained"], pred["generated_at"] = meta["trained"], started.strftime("%Y-%m-%dT%H:%M:%SZ")

    stem = f"{hour:%Y/%m/%d/%H}.parquet"
    save(pred, out / "predictions" / stem)
    if keep_inputs:                                        # the model's columns only
        window = [c for c in rows.columns if "|" in c]
        path = out / "inputs" / f"{hour:%Y/%m/%d/%H}.csv.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows[["region_fips", "has_weather"] + base + window].to_csv(path, index=False, float_format="%.4g")
    names = regions.set_index("region_fips")
    latest = {                                             # counties: [fips, chance, low, high, alert]
        "decision_hour": f"{hour:%Y-%m-%dT%H:%MZ}", "window": [f"{pred.window_start[0]:%Y-%m-%dT%H:%MZ}",
                                                             f"{pred.window_end[0]:%Y-%m-%dT%H:%MZ}"],
        "generated_at": pred.generated_at[0], "model_trained": meta["trained"], "alert_level": level,
        "runs_used": sorted(f"{hour - pd.Timedelta(hours=a):%Y-%m-%dT%HZ}" for a in probs),
        "counties": [[r.region_fips, round(float(r.p_mean), 4), round(float(r.p_low), 4), round(float(r.p_high), 4),
                      int(r.alert)] for r in pred.itertuples()],
    }
    (out / "latest.json").write_text(json.dumps(latest, separators=(",", ":")))
    top = pred.nlargest(3, "p_mean")
    highest = ", ".join(f"{names.region[f]} {v:.1%}" for f, v in zip(top.region_fips, top.p_mean, strict=True))
    print(f"{hour:%Y-%m-%d %H}Z: {len(pred)} counties, {p.shape[1]} runs, {int(pred.alert.sum())} alerts, "
          f"highest {highest}")
    return pred


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", help="decision hour, UTC (default: the current hour)")
    parser.add_argument("--out", default=str(Path(__file__).parent / "out"))
    parser.add_argument("--inputs", action="store_true", help="also save the inputs (the shakedown's feed check)")
    args = parser.parse_args()
    hour = pd.Timestamp(args.hour) if args.hour else pd.Timestamp.now(tz="UTC").tz_localize(None).floor("h")
    run(hour, Path(args.out), args.inputs)


if __name__ == "__main__":
    main()
