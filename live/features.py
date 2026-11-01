"""The live model's inputs, computed from raw feeds the way the warehouse computes them for training.

Each function mirrors one dbt model, so the live job and the training table agree; live/parity.py checks this by
feeding these functions the warehouse's own raw tables and comparing with marts.mart_study__region_1h.

  hourly_weather   stg_hrrr__hourly + the per-hour columns of mart_study__region_1h
  weather_6h       the "weather: the 6 hours before `hour`" summaries of mart_study__region_1h
  warnings_1h      the warnings half of int_study__nws_1h
  outlooks_1h      the outlook half of int_study__nws_1h
  neighbors        ml.data.neighbor_features, without the outage columns
  model_rows       all of it for a set of decision hours, plus ml.data.add_derived and the forecast window

A decision at `hour` sees weather up to hour - 1, warnings and outlooks issued before `hour`: as in training.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from ml import data
from ml.forecast_test import window_from_forecast

STATIC = Path(__file__).parent / "static"
STATES = {"IL": "17", "MO": "29"}
CATEGORICAL = {"TSTM": 1, "MRGL": 2, "SLGT": 3, "ENH": 4, "MDT": 5, "HIGH": 6}
OUTAGE_INPUTS = ["pct_out_now", "max_pct_out_prev_24h", "near_pct_out_max", "up_pct_out_max"]


def region_fips(fips):
    """dbt macro region_fips: St. Louis City and County are one region."""
    return fips.where(~fips.isin(["29189", "29510"]), "29189+29510")


def hourly_weather(raw):
    """Open-Meteo hourly columns (region_fips, time, wind_gusts_10m, ...) -> the mart's per-hour weather."""
    rad10, rad500 = np.radians(raw.wind_direction_10m), np.radians(raw.wind_direction_500hPa)
    u10, v10 = -raw.wind_speed_10m * np.sin(rad10), -raw.wind_speed_10m * np.cos(rad10)
    u500, v500 = -raw.wind_speed_500hPa * np.sin(rad500), -raw.wind_speed_500hPa * np.cos(rad500)
    return pd.DataFrame({
        "region_fips": raw.region_fips, "hour": pd.to_datetime(raw.time),
        "gust_ms": raw.wind_gusts_10m, "wind10_ms": raw.wind_speed_10m, "wind850_ms": raw.wind_speed_850hPa,
        "cape_jkg": raw.cape, "temp_c": raw.temperature_2m, "freezing_level_m": raw.freezing_level_height,
        "precip_mm": raw.precipitation.where(raw.precipitation <= 100),        # > 100 mm/h: an archive artifact
        "shear_ms": np.sqrt((u500 - u10) ** 2 + (v500 - v10) ** 2),
    })


def weather_6h(hw, hours):
    """Per region and decision hour in `hours`: summaries over the 6 hours before it."""
    parts = []
    for fips, r in hw.groupby("region_fips"):
        r = r.set_index("hour").sort_index()
        r = r.reindex(pd.date_range(min(r.index.min(), hours.min() - pd.Timedelta(hours=6)), hours.max(), freq="h"))
        icing = ((r.temp_c <= 0) & (r.precip_mm > 0)).astype(float)
        hail = ((r.cape_jkg >= 500) & (r.precip_mm >= 2) & (r.freezing_level_m <= 3500)).astype(float)
        roll = lambda s, f: getattr(s.rolling(6, min_periods=1), f)().shift(1)        # noqa: E731  rows h-6..h-1
        out = pd.DataFrame({
            "has_weather": r.gust_ms.rolling(6, min_periods=1).count().shift(1) == 6,
            "gust_max_ms": roll(r.gust_ms, "max"), "wind10_max_ms": roll(r.wind10_ms, "max"),
            "wind850_max_ms": roll(r.wind850_ms, "max"), "shear_0_6km_max_ms": roll(r.shear_ms, "max"),
            "cape_max_jkg": roll(r.cape_jkg, "max"),
            # SQL sum() ignores NULLs and is NULL only when every value is
            "precip_sum_mm": r.precip_mm.rolling(6, min_periods=1).sum().shift(1)
                             .where(r.precip_mm.rolling(6, min_periods=1).count().shift(1) > 0),
            "precip_max_1h_mm": roll(r.precip_mm, "max"), "temp_min_c": roll(r.temp_c, "min"),
            "temp_mean_c": roll(r.temp_c, "mean"), "freezing_level_min_m": roll(r.freezing_level_m, "min"),
            "icing_hours": icing.rolling(6, min_periods=1).sum().shift(1),
            "hail_hours": hail.rolling(6, min_periods=1).sum().shift(1),
        })
        parts.append(out.reindex(hours).assign(region_fips=fips))
    return pd.concat(parts).rename_axis("hour").reset_index()


def warnings_1h(rows, hours):
    """IEM warning rows (ugc, phenomena, significance, utc_issue, utc_expire) -> warnings in force at each hour:
    a warning counts for an hour that starts strictly inside (issue, expire)."""
    zones = pd.read_parquet(STATIC / "zones.parquet")
    w = rows[rows.significance == "W"].copy()
    w["issue"], w["expire"] = pd.to_datetime(w.utc_issue), pd.to_datetime(w.utc_expire)
    w = w[w.expire > w.issue]
    w["state"], w["kind"], w["number"] = w.ugc.str[:2], w.ugc.str[2], w.ugc.str[3:]
    counties = w[w.kind == "C"].assign(fips_code=lambda d: d.state.map(STATES) + d.number)
    by_zone = w[w.kind == "Z"].assign(zone_id=lambda d: d.state + d.number).merge(zones, on="zone_id")
    w = pd.concat([counties, by_zone], ignore_index=True)
    w["region_fips"] = region_fips(w.fips_code)
    w["first"] = w.issue.dt.floor("h") + pd.Timedelta(hours=1)
    w["last"] = (w.expire - pd.Timedelta(minutes=1)).dt.floor("h")
    out = []
    for h in hours:
        on = w[(w["first"] <= h) & (w["last"] >= h)]
        g = on.groupby("region_fips").phenomena
        out.append(pd.DataFrame({
            "warn_svr": g.agg(lambda p: (p == "SV").any()), "warn_tor": g.agg(lambda p: (p == "TO").any()),
            "warn_wind": g.agg(lambda p: (p == "HW").any()),
            "warn_winter": g.agg(lambda p: p.isin(["IS", "WS", "BZ"]).any()),
        }).assign(hour=h))
    return pd.concat(out).rename_axis("region_fips").reset_index() if out else pd.DataFrame()


def outlook_table(polygons, regions):
    """SPC Day 1 polygons (IEM shapefile) -> one row per product x region, as fetch_nws.fetch_outlooks writes:
    0 where a product doesn't reach a region."""
    import geopandas as gpd
    points = gpd.GeoDataFrame(regions[["region_fips"]],
                              geometry=gpd.points_from_xy(regions.outlook_lon, regions.outlook_lat), crs="EPSG:4326")
    polygons = polygons.to_crs(points.crs)
    hits = gpd.sjoin(points, polygons, predicate="within")
    hits["level"] = hits["THRESHOLD"].map(CATEGORICAL)
    hits["prob"] = pd.to_numeric(hits["THRESHOLD"], errors="coerce")       # SIGN / CIG (hatched) -> unknown
    keys = ["PRODISS", "ISSUE", "EXPIRE", "region_fips"]
    by_category = hits.pivot_table(index=keys, columns="CATEGORY", values=["level", "prob"], aggfunc="max")
    covered = pd.DataFrame({
        "spc_cat": by_category.get(("level", "CATEGORICAL")), "spc_wind_prob": by_category.get(("prob", "WIND")),
        "spc_tor_prob": by_category.get(("prob", "TORNADO")), "spc_hail_prob": by_category.get(("prob", "HAIL")),
    }, index=by_category.index)
    products = polygons[keys[:-1]].drop_duplicates()
    full = products.merge(points[["region_fips"]], how="cross").set_index(keys)
    t = full.join(covered).fillna(0).reset_index()
    return pd.DataFrame({
        "issued_utc": pd.to_datetime(t.PRODISS, format="%Y%m%d%H%M"),
        "valid_from": pd.to_datetime(t.ISSUE, format="%Y%m%d%H%M"),
        "valid_to": pd.to_datetime(t.EXPIRE, format="%Y%m%d%H%M"),
        "region_fips": t.region_fips, "spc_cat": t.spc_cat.astype(float).astype(int),
        **{c: t[c].astype(float) for c in ("spc_wind_prob", "spc_tor_prob", "spc_hail_prob")},
    })


def outlooks_1h(table, hours):
    """The latest product issued before each hour and valid at it."""
    products = table[["issued_utc", "valid_from", "valid_to"]].drop_duplicates()
    out = []
    for h in hours:
        ok = products[(products.issued_utc < h) & (products.valid_from <= h) & (products.valid_to > h)]
        if len(ok):
            latest = table[table.issued_utc == ok.issued_utc.max()]
            out.append(latest.drop(columns=["issued_utc", "valid_from", "valid_to"]).assign(hour=h))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["region_fips", "hour"])


def neighbors(base):
    """base: region_fips, hour, gust_max_ms, cape_max_jkg, precip_sum_mm, warn (svr or tor) -> near_* / up_*."""
    pairs = pd.read_parquet(STATIC / "neighbors.parquet")
    sources = {"gust_max_ms": ("gust_max_ms", "max"), "cape_max_jkg": ("cape_max_jkg", "max"),
               "precip_max_mm": ("precip_sum_mm", "max"), "warn_share": ("warn", "mean")}
    out = base[["region_fips", "hour"]].copy()
    for kind, flag in (("near", "is_near"), ("up", "is_upwind")):
        p = pairs[pairs[flag]][["region_fips", "neighbor_fips"]]
        j = p.merge(base.rename(columns={"region_fips": "neighbor_fips"}), on="neighbor_fips")
        agg = j.groupby(["region_fips", "hour"]).agg(**{f"{kind}_{n}": (s, f) for n, (s, f) in sources.items()})
        out = out.merge(agg.reset_index(), on=["region_fips", "hour"], how="left")
    return out


def model_rows(hw, warning_rows, outlook_table_, hours, forecast_runs=None, run_ages=(2, 3, 4, 5, 6)):
    """Every region at every decision hour in `hours`, with the live model's inputs. forecast_runs: HRRR point
    forecasts (ingest.fetch_hrrr_forecast.fetch_run rows); each run age adds the window columns as
    `<column>|<age>` (forecast_test.WINDOW)."""
    hours = pd.DatetimeIndex(hours)
    regions = pd.read_parquet(STATIC / "regions.parquet")
    df = weather_6h(hw, hours)
    warn = warnings_1h(warning_rows, hours)
    df = df.merge(warn, on=["region_fips", "hour"], how="left") if len(warn) else df.assign(
        warn_svr=False, warn_tor=False, warn_wind=False, warn_winter=False)
    for c in ["warn_svr", "warn_tor", "warn_wind", "warn_winter"]:
        df[c] = df[c].astype("boolean").fillna(False).astype(bool)
    df = df.merge(outlooks_1h(outlook_table_, hours), on=["region_fips", "hour"], how="left")
    base = df[["region_fips", "hour", "gust_max_ms", "cape_max_jkg", "precip_sum_mm"]].assign(
        warn=(df.warn_svr | df.warn_tor).astype(float))
    df = df.merge(neighbors(base), on=["region_fips", "hour"], how="left")
    df = df.merge(regions[["region_fips", "customers", "housing_per_km2", "share_homes_pre1960",
                           "median_year_built", "canopy_mean_pct", "canopy_dense_share"]], on="region_fips")
    df["month"], df["block_hour_utc"] = df.hour.dt.month, df.hour.dt.hour
    df["precip_prev_72h_mm"] = np.nan                     # add_derived uses it; not a live model input
    df = data.add_derived(df.rename(columns={"hour": "block_start"}))
    if forecast_runs is not None:
        f = forecast_runs.copy()
        f["wind10_ms"], f["wind850_ms"] = np.hypot(f.u10, f.v10), np.hypot(f.u850, f.v850)
        for age in run_ages:
            w = window_from_forecast(f, age)
            w = w.rename(columns={c: f"{c}|{age}" for c in w.columns if c.startswith("win_")})
            df = df.merge(w, on=["region_fips", "block_start"], how="left")
    return df


def live_features():
    """The live model's inputs (forecast_test.WINDOW last), in training order."""
    from ml.forecast_test import WINDOW
    from ml.moving_window import FEATURES
    return [c for c in data.resolve_features(FEATURES) if c not in OUTAGE_INPUTS] + WINDOW
