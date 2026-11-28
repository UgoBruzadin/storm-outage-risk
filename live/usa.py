"""One hour of the USA live forecast (live/model_usa): every county of the 48 states.

As live/predict.py, with three differences:

  weather     every input comes from the HRRR archive on AWS (hrrrzarr), not Open-Meteo: Open-Meteo's past hour h is
              HRRR run h-1, forecast hour 1, to rounding (checked on 60 counties x 8 hours of 2025, every variable),
              and asking Open-Meteo for 3,089 points every hour is far over its free limit
  past hours  the five runs read for the window ahead (issued 2-6 h before) give the past hours h-1 ... h-5; the
              rest come from a store of past hours (--store), filled from the archive when missing: every variable
              for the 6 hours before h (the 6-hour summaries), rain alone back to 72 hours (precip_prev_72h_mm,
              unknown unless all 72 hours are known, as mart_study__region_1h)
  inputs      the E55 inputs on top of the MO + IL ones: duration / spread over the window (forecast_test.summarize,
              as usa_final_test.scored_states), roads + street canopy, location, history as of Jan 1, the E47
              place files and soil x recent rain (static_usa/, exported by live.static --usa)

Writes under --out, as live/predict.py: predictions/<YYYY>/<MM>/<DD>/<HH>.parquet, latest.json, and with --inputs the
inputs behind them.

Usage: pixi run python -m live.usa [--hour 2026-11-20T18] [--out live/out_usa] [--store live/out_usa/store.parquet]
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ingest import fetch_hrrr_forecast as fh
from live import features as lf
from live import sources
from live.predict import save

HERE = Path(__file__).parent
MODEL = HERE / "model_usa"
STATIC = HERE / "static_usa"
FULL_HOURS, RAIN_HOURS, KEEP_HOURS = 6, 72, 80      # every variable 6 h back, rain 72 h back; the store keeps 80
RAW = list(fh.VARIABLES)                            # gust_ms, u10, ..., temp_k, freezing_level_m

# What drives a county's chance, in words a reader knows: each input's share of the model's log-odds (XGBoost's own
# per-row contributions, the newest run's window), summed by group. Checked in this order, first match wins.
DRIVER_GROUPS = [
    ("soaked ground", ("wind_x_wet_soil", "precip_prev_72h", "poor_drain", "soil_")),
    ("ice or freezing rain", ("icing", "freezing_level", "temp_", "warn_winter")),
    ("official warnings", ("warn_", "spc_")),
    ("thunderstorms", ("cape", "shear", "hail")),
    ("strong gusts", ("gust", "wind")),
    ("heavy rain", ("precip",)),
    ("trees", ("canopy", "road_treed", "tm_", "stand_age")),
    ("past outages here", ("hist_",)),
    ("the local grid", ("util_", "transmission", "log_road", "log_customers", "housing", "homes", "year_built")),
    ("season and place", ("month", "block_hour", "lat", "lon", "water_share", "river", "stream", "flood")),
]
DRIVER_MIN_P, DRIVER_MIN_LOGIT = 0.03, 0.1           # explain counties at 3% or more; groups adding 0.1 or more


# ---------- past hours ----------

def fetch_first_hour(run, points, pool, variables, fhour=1):
    """Forecast hour `fhour` of one run (the hour run + fhour) at every region point, for `variables`; None if
    the run is missing from the archive."""
    fips, trow, tcol, irow, icol = points
    tiles = sorted(set(zip(trow, tcol, strict=True)))
    stem = f"{fh.BASE}/{run:%Y%m%d}/{run:%Y%m%d_%H}z_fcst.zarr"
    jobs = {(name, t): f"{stem}/{fh.VARIABLES[name]}/{fh.VARIABLES[name].split('/')[0]}/"
                       f"{fh.VARIABLES[name].split('/')[1]}/0.{t[0]}.{t[1]}" for name in variables for t in tiles}
    raw = dict(zip(jobs, pool.map(fh.get, jobs.values()), strict=True))
    if any(v is None for v in raw.values()):
        return None
    out = {"region_fips": fips, "hour": run + pd.Timedelta(hours=fhour)}
    for name in variables:
        v = np.full(len(fips), np.nan, dtype="float32")
        for t in tiles:
            cube = np.frombuffer(fh.BLOSC.decode(raw[(name, t)]), dtype="<f4").reshape(-1, fh.TILE, fh.TILE)
            here = (trow == t[0]) & (tcol == t[1])
            if len(cube) < fhour:
                return None
            v[here] = cube[fhour - 1][irow[here], icol[here]]            # index i = forecast hour i + 1
        v[v == -9999.0] = np.nan
        out[name] = v
    return pd.DataFrame(out)


def points(regions):
    return tuple(regions[c].to_numpy() for c in ("region_fips", "tile_row", "tile_col", "row", "col"))


def update_store(store, hour, forecast_runs, regions, pool):
    """The past hours the decision at `hour` needs, from the store, the runs already read, and the archive."""
    fresh = forecast_runs[forecast_runs.fhour == 1][["region_fips", "hour", *RAW]] if forecast_runs is not None \
        else store.head(0)
    store = pd.concat([store[~store.hour.isin(fresh.hour.unique())], fresh], ignore_index=True)
    store = store[store.hour >= hour - pd.Timedelta(hours=KEEP_HOURS)]
    full = store.dropna(subset=["gust_ms"]).groupby("hour").size()
    rain = store.dropna(subset=["precip_mm"]).groupby("hour").size()
    n, pts, got = len(regions), points(regions), []
    for back in range(1, RAIN_HOURS + 1):
        h = hour - pd.Timedelta(hours=back)
        need = RAW if back <= FULL_HOURS else ["precip_mm"]
        have = (full if back <= FULL_HOURS else rain).get(h, 0)
        if have >= n:
            continue
        for k in (1, 2, 3):          # a run missing from the archive: the hour from the next older runs instead
            part = fetch_first_hour(h - pd.Timedelta(hours=k), pts, pool, need, fhour=k)
            if part is not None:
                got.append(part)
                if k > 1:
                    print(f"  {h}: run {h - pd.Timedelta(hours=1)} missing, used forecast hour {k}", flush=True)
                break
    if got:
        new = pd.concat(got, ignore_index=True)
        old = store.set_index(["region_fips", "hour"])
        new = new.set_index(["region_fips", "hour"])
        store = new.combine_first(old).reset_index()                    # fetched values win; other columns kept
    store = store.astype({c: "float32" for c in RAW})                      # an empty store starts untyped
    print(f"past hours: {len(got)} fetched from the archive, store {store.hour.nunique()} hours", flush=True)
    return store.sort_values(["hour", "region_fips"]).reset_index(drop=True)


def rain(mm):
    """Hourly rain as training saw it: Open-Meteo's 0.01 mm (a trace under 0.005 mm is dry: icing and hail hours
    count rain > 0); over 100 mm/h is an archive artifact, unknown."""
    mm = mm.astype("float64").round(2)
    return mm.where(mm <= 100)


def hourly(store):
    """Store rows -> the per-hour weather of mart_study__region_1h (lf.hourly_weather's columns), rounded as
    Open-Meteo rounds the past hours training used (0.01 m/s, 0.01 C, 0.1 m, 0.01 mm)."""
    s = store.dropna(subset=["gust_ms"]).astype({c: "float64" for c in RAW})
    return pd.DataFrame({
        "region_fips": s.region_fips, "hour": s.hour, "gust_ms": s.gust_ms.round(2),
        "wind10_ms": np.hypot(s.u10, s.v10).round(2), "wind850_ms": np.hypot(s.u850, s.v850).round(2),
        "cape_jkg": s.cape_jkg, "temp_c": (s.temp_k - 273.15).round(2), "freezing_level_m": s.freezing_level_m.round(1),
        "precip_mm": rain(s.precip_mm), "shear_ms": np.hypot(s.u500 - s.u10, s.v500 - s.v10),
    })


def precip_72h(store, hour):
    """precip_prev_72h_mm at `hour`: the sum over hours h-72 ... h-1, unknown unless all 72 are known."""
    hours = pd.date_range(hour - pd.Timedelta(hours=RAIN_HOURS), hour - pd.Timedelta(hours=1), freq="h")
    s = store[store.hour.isin(hours)]
    p = rain(s.precip_mm)
    g = p.groupby(s.region_fips)
    out = g.sum().where(g.count() == RAIN_HOURS)
    return pd.DataFrame({"region_fips": out.index, "hour": hour, "precip_prev_72h_mm": out.to_numpy()})


def forecasts(regions, runs):
    """sources.forecasts with the runs fetched side by side (each its own pool): the whole country's five runs in
    about the time of one."""
    pts = points(regions)

    def one(run):
        with ThreadPoolExecutor(max_workers=16) as pool:
            return fh.fetch_run(run, pts, pool)
    with ThreadPoolExecutor(max_workers=len(runs)) as outer:
        found = [df for df in outer.map(one, runs) if df is not None]
    if not found:
        return None
    df = pd.concat(found, ignore_index=True)
    df["temp_c"] = df.temp_k - 273.15                                  # temp_k kept for the past-hours store
    df["region_fips"] = df.region_fips.astype(str)
    return df.astype({c: np.float32 for c in df.columns if df[c].dtype == np.float64})


# ---------- inputs ----------

def add_static(df):
    """The E55 inputs that don't change with the weather (ml.data.add_static / usa_ablation.add_inputs)."""
    place = pd.read_parquet(STATIC / "place.parquet")
    hist = pd.read_parquet(STATIC / "history.parquet")
    df = df.merge(place.drop(columns=[c for c in place if c in df and c != "region_fips"]), on="region_fips",
                  how="left", validate="m:1")
    df["log_road_per_customer"] = np.log10(df.pop("road_km")) - df.log_customers
    df = df.merge(hist, on="region_fips", how="left", validate="m:1")
    df["poor_drain_x_rain"] = df.soil_poor_drain_share * df.precip_prev_72h_mm
    df["poor_drain_x_wind_rain"] = df.soil_poor_drain_share * df.wind_x_wet_soil
    return df


def model_rows(store, warning_rows, outlook_table_, hour, forecast_runs, run_ages):
    rows = lf.model_rows(hourly(store), warning_rows, outlook_table_, [hour], forecast_runs, run_ages, static=STATIC,
                         precip_72h=precip_72h(store, hour))
    return add_static(rows)


# ---------- one hour ----------

def driver_group(feature):
    name = feature.removeprefix("win_").removeprefix("near_").removeprefix("up_")
    return next((g for g, keys in DRIVER_GROUPS if any(k in name for k in keys)), "season and place")


def drivers(model, x, fips, p, min_p=DRIVER_MIN_P, top=3):
    """{fips: [[group, log-odds added], ...]}: the largest positive groups of each county at min_p or more."""
    from xgboost import DMatrix
    keep = np.flatnonzero(p >= min_p)
    if not len(keep):
        return {}
    contrib = model.get_booster().predict(DMatrix(x.iloc[keep]), pred_contribs=True)[:, :-1]   # last = bias
    groups = pd.DataFrame(contrib, columns=x.columns).T.groupby(lambda c: driver_group(c), sort=False).sum().T
    out = {}
    for i, row in zip(keep, groups.itertuples(index=False), strict=True):
        g = sorted(((n, v) for n, v in zip(groups.columns, row, strict=True) if v >= DRIVER_MIN_LOGIT),
                   key=lambda t: -t[1])[:top]
        out[fips[i]] = [[n, round(float(v), 2)] for n, v in g]
    return out


def run(hour, out, store_path, keep_inputs=False):
    meta = json.loads((MODEL / "meta.json").read_text())
    model = XGBClassifier()
    model.load_model(MODEL / "model.json")
    regions = pd.read_parquet(STATIC / "regions.parquet")
    started = datetime.now(UTC)

    tick = lambda what: print(f"  {what}: {(datetime.now(UTC) - started).seconds} s", flush=True)  # noqa: E731
    warn = sources.warnings(hour - pd.Timedelta(days=3), hour)
    tick("warnings")
    table = lf.outlook_table(sources.outlooks(hour - pd.Timedelta(days=2), hour), regions)
    tick("outlooks")
    runs = [hour - pd.Timedelta(hours=a) for a in meta["run_ages"]]
    fc = forecasts(regions, runs)
    tick("forecast runs")
    store = pd.read_parquet(store_path) if store_path.exists() else pd.DataFrame(
        columns=["region_fips", "hour", *RAW]).astype({"region_fips": str, "hour": "datetime64[us]"})
    with ThreadPoolExecutor(max_workers=16) as pool:
        store = update_store(store, hour, fc, regions, pool)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store.to_parquet(store_path, index=False, compression="zstd")
    tick("past hours")
    rows = model_rows(store, warn, table, hour, fc, meta["run_ages"])
    tick("inputs")

    features = meta["features"]
    window = [c for c in features if c.startswith("win_")]
    base = [c for c in features if c not in window]
    probs, newest = {}, None
    for age in meta["run_ages"]:
        cols = [f"{c}|{age}" for c in window]
        if cols[0] not in rows or rows[cols[0]].isna().all():
            continue
        x = rows[base].copy()
        x[window] = rows[cols].to_numpy()
        probs[age] = model.predict_proba(x[features].astype("float32"))[:, 1]
        newest = newest if newest is not None else x[features].astype("float32")
    if not probs:
        raise RuntimeError(f"no HRRR run issued 2-6 hours before {hour} is in the archive yet")
    p = np.column_stack(list(probs.values()))

    level = meta["alert_level"]
    pred = pd.DataFrame({
        "decision_hour": hour, "region_fips": rows.region_fips,
        "window_start": hour + pd.Timedelta(hours=meta["lead_hours"]),
        "window_end": hour + pd.Timedelta(hours=meta["lead_hours"] + 6),
        "p_mean": p.mean(axis=1), "p_low": p.min(axis=1), "p_high": p.max(axis=1), "n_runs": p.shape[1],
        "has_weather": rows.has_weather.to_numpy(), "has_rain_72h": rows.precip_prev_72h_mm.notna().to_numpy(),
    })
    pred["alert"] = pred.p_mean >= level
    pred["model_trained"], pred["generated_at"] = meta["trained"], started.strftime("%Y-%m-%dT%H:%M:%SZ")

    save(pred, out / "predictions" / f"{hour:%Y/%m/%d/%H}.parquet")
    if keep_inputs:
        cols = [c for c in rows.columns if "|" in c]
        path = out / "inputs" / f"{hour:%Y/%m/%d/%H}.csv.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows[["region_fips", "has_weather"] + base + cols].to_csv(path, index=False, float_format="%.4g")
    latest = {                                             # counties: [fips, chance, low, high, alert]
        "decision_hour": f"{hour:%Y-%m-%dT%H:%MZ}", "window": [f"{pred.window_start[0]:%Y-%m-%dT%H:%MZ}",
                                                             f"{pred.window_end[0]:%Y-%m-%dT%H:%MZ}"],
        "generated_at": pred.generated_at[0], "model_trained": meta["trained"], "alert_level": level,
        "runs_used": sorted(f"{hour - pd.Timedelta(hours=a):%Y-%m-%dT%HZ}" for a in probs),
        "counties": [[r.region_fips, round(float(r.p_mean), 4), round(float(r.p_low), 4), round(float(r.p_high), 4),
                      int(r.alert)] for r in pred.itertuples()],
    }
    latest["drivers"] = drivers(model, newest, rows.region_fips.to_numpy(), pred.p_mean.to_numpy())
    (out / "latest.json").write_text(json.dumps(latest, separators=(",", ":")))
    names = regions.set_index("region_fips")
    top = pred.nlargest(3, "p_mean")
    highest = ", ".join(f"{names.region[f]}, {names.state[f]} {v:.1%}" for f, v in zip(top.region_fips, top.p_mean,
                                                                                       strict=True))
    print(f"{hour:%Y-%m-%d %H}Z: {len(pred)} counties, {p.shape[1]} runs, {int(pred.alert.sum())} alerts, "
          f"rain 72 h known for {pred.has_rain_72h.mean():.0%}, {(datetime.now(UTC) - started).seconds} s; "
          f"highest {highest}")
    return pred, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", help="decision hour, UTC (default: the current hour)")
    parser.add_argument("--out", default=str(HERE / "out_usa"))
    parser.add_argument("--store", help="the past-hours store (default: <out>/store.parquet)")
    parser.add_argument("--inputs", action="store_true", help="also save the inputs (the feed check)")
    args = parser.parse_args()
    hour = pd.Timestamp(args.hour) if args.hour else pd.Timestamp.now(tz="UTC").tz_localize(None).floor("h")
    out = Path(args.out)
    run(hour, out, Path(args.store) if args.store else out / "store.parquet", args.inputs)


if __name__ == "__main__":
    main()
