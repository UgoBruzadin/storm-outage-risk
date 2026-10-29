"""Load the modeling table and define feature groups.

One row = one region x one 6-hour block, from marts.mart_study__region_6h,
plus the region's resilience history and a few "recent outage" features.

Feature groups are combined by name in benchmark configs:
    "weather+place+history"   -> union of the three groups
    "weather+place-canopy"    -> minus every feature in the "canopy" group
"""
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "warehouse.duckdb"

FEATURE_GROUPS = {
    # storm ingredients (HRRR) + interaction terms + calendar
    "weather": [
        "gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms",
        "cape_max_jkg", "precip_sum_mm", "precip_max_1h_mm", "temp_min_c",
        "temp_mean_c", "freezing_level_min_m", "icing_hours", "hail_hours",
        "wind_x_precip", "wind_squared", "shear_x_cape", "month", "block_hour_utc",
    ],
    # what the place is like — fixed per region
    "place": [
        "log_customers", "housing_per_km2", "share_homes_pre1960",
        "median_year_built", "canopy_mean_pct", "canopy_dense_share",
    ],
    # subset of "place", for ablations: "weather+place-canopy"
    "canopy": ["canopy_mean_pct", "canopy_dense_share"],
    # official forecasts: NWS warnings in force during the block, SPC Day 1 outlook at its start
    "warnings": ["warn_svr", "warn_tor", "warn_wind", "warn_winter"],
    "outlook": ["spc_cat", "spc_wind_prob", "spc_tor_prob", "spc_hail_prob"],
    # weathernext-outage-forecasting's feature list, mapped to the closest HRRR columns:
    # 925 hPa wind -> 850 hPa, 700 hPa updraft -> CAPE, 700/850 hPa temperature -> 2 m,
    # hail flag -> hail_hours; interactions built from sustained 10 m wind as theirs are
    "weathernext": [
        "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms", "cape_max_jkg", "precip_sum_mm",
        "temp_min_c", "temp_mean_c", "hail_hours", "block_hour_utc", "day_of_week", "month",
        "wn_wind_x_precip", "wn_wind_squared", "shear_x_cape",
    ],
    # rain before the block (wet ground); opt-in: mixed across seeds (benchmarks/seeds_ablate.yaml)
    "wet_soil": ["precip_prev_72h_mm", "precip_prev_7d_mm", "wind_x_wet_soil"],
    # the region's own track record over the 3 years before the row's year (as of Jan 1)
    "history": [
        "hist_hours_out_per_customer", "hist_events_per_year", "hist_storm_hit_rate",
        "hist_quiet_event_rate", "hist_repeat_7d_share",
    ],
    # outages known at the start of the block: the previous block(s) are over.
    # Persistence is strong — a model that ignores it is handicapped.
    "recent": ["prev_block_pct_out", "max_pct_out_prev_24h"],
    # moving-window table (load_hourly): outages in the hour before the decision, and the past day
    "recent_now": ["pct_out_now", "max_pct_out_prev_24h"],
    # moving-window table: how long since the last >= 1% outage, how big it was, the worst of the past week
    "since": ["hours_since_outage", "last_outage_pct", "max_pct_out_prev_7d"],
    # moving-window table: rain in the 72 hours before the decision (the hourly version of wet_soil)
    "wet_72h": ["precip_prev_72h_mm", "wind_x_wet_soil"],
    # moving-window table: neighbouring regions at the decision time (neighbor_features)
    "neighbors": ["near_gust_max_ms", "near_cape_max_jkg", "near_precip_max_mm", "near_pct_out_max",
                  "near_warn_share", "up_gust_max_ms", "up_cape_max_jkg", "up_precip_max_mm", "up_pct_out_max",
                  "up_warn_share"],
}


def resolve_features(spec):
    """'weather+place-canopy' -> ordered list of column names."""
    features, sign, token = [], "+", ""
    for ch in spec + "+":
        if ch in "+-":
            if token:
                group = FEATURE_GROUPS[token]
                features = features + [f for f in group if f not in features] if sign == "+" \
                    else [f for f in features if f not in group]
            sign, token = ch, ""
        else:
            token += ch
    return features


def load(threshold_pct, years, db=DB):
    """Every usable region-block in `years` with features (and the label, if threshold_pct is given)."""
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        WITH m AS (
            -- recent-outage features use the full grid (before filtering), so the
            -- first block of a year still sees the last blocks of the previous one
            SELECT
                *,
                lag(peak_pct_out) OVER w                                        AS prev_block_pct_out,
                max(peak_pct_out) OVER (w ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) AS max_pct_out_prev_24h
            FROM marts.mart_study__region_6h
            WINDOW w AS (PARTITION BY region_fips ORDER BY block_start)
        )
        SELECT
            m.*,
            h.hours_out_per_customer  AS hist_hours_out_per_customer,
            h.events_per_year         AS hist_events_per_year,
            h.storm_hit_rate          AS hist_storm_hit_rate,
            h.quiet_event_rate        AS hist_quiet_event_rate,
            h.repeat_7d_share         AS hist_repeat_7d_share,
            h.history_end
        FROM m
        -- the track record as of Jan 1 of the row's own year (3 years before it only)
        LEFT JOIN marts.mart_study__region_history_asof AS h
               ON h.region_fips = m.region_fips AND h.as_of_year = year(m.block_start)
        WHERE m.has_weather
          AND m.peak_pct_out IS NOT NULL
          -- the years asked for, not every year between the first and last
          AND year(m.block_start) IN ({", ".join(str(int(y)) for y in years)})
        -- a fixed row order: DuckDB's parallel scan returns rows in varying order, and
        -- row subsampling in the tree models depends on it, so without this the same
        -- run gives slightly different scores (~1%) each time
        ORDER BY m.region_fips, m.block_start
    """).df()
    con.close()
    df = add_derived(df)
    return label(df, threshold_pct) if threshold_pct is not None else df


HOURLY_LEADS = (0, 1, 2, 3, 6)


def load_hourly(threshold_pct, years, lead, onsets_only=True, neighbors=True, db=DB):
    """The moving-window table (marts.mart_study__region_1h) for one lead: a row is a decision at the
    start of `hour` about the 6 hours starting `lead` hours later. Features use only what had happened
    by `hour`; y = the window's worst hour >= threshold_pct; is_onset = the region was known to be below
    the threshold when the window began. Columns are renamed so the 6-hour feature groups apply:
    hour -> block_start (the decision time), hour_utc -> block_hour_utc."""
    if lead not in HOURLY_LEADS:
        raise ValueError(f"lead must be one of {HOURLY_LEADS}")
    con = duckdb.connect(str(db), read_only=True)
    others = ", ".join(f"fut_max_pct_{x}, start_pct_{x}" for x in HOURLY_LEADS)
    df = con.sql(f"""
        SELECT * EXCLUDE ({others}, hour, hour_utc),
               hour AS block_start, hour_utc AS block_hour_utc,
               fut_max_pct_{lead} AS fut_max_pct, start_pct_{lead} AS start_pct
        FROM marts.mart_study__region_1h
        -- only region-years EAGLE-I was tracking (mart_study__region_coverage)
        SEMI JOIN marts.mart_study__region_coverage AS c
               ON c.region_fips = mart_study__region_1h.region_fips AND c.year = year(hour) AND c.tracked
        WHERE has_weather
          AND fut_max_pct_{lead} IS NOT NULL
          AND year(hour) IN ({", ".join(str(int(y)) for y in years)})
          {f"AND start_pct_{lead} < {float(threshold_pct)}" if onsets_only else ""}
        ORDER BY region_fips, hour
    """).df()
    con.close()
    if neighbors:
        nb = neighbor_features(db=db).rename(columns={"hour": "block_start"})
        df = df.merge(nb, on=["region_fips", "block_start"], how="left")
    df = add_derived(df)
    df["y"] = (df["fut_max_pct"] >= threshold_pct).astype(int)
    df["is_onset"] = df["start_pct"].notna() & (df["start_pct"] < threshold_pct)
    return df


NEIGHBOR_CACHE = ROOT / "data" / "cache" / "neighbors_1h.parquet"


def neighbor_features(db=DB, cache=NEIGHBOR_CACHE):
    """For every region and hour, its neighbours' known-by-then features (mart_study__region_1h):
    the strongest gust and CAPE and the most rain in the past 6 hours, the worst outage in the
    hour before, and the share with a severe thunderstorm or tornado warning in force; near_* =
    within 100 km, up_* = upwind (intermediate.int_study__region_neighbors). Computed as
    hour x region arrays (a SQL join would be ~400M rows) and cached; delete the cache after a
    dbt build."""
    if cache.exists():
        return pd.read_parquet(cache)
    con = duckdb.connect(str(db), read_only=True)
    base = con.sql("""
        SELECT region_fips, hour, gust_max_ms, cape_max_jkg, precip_sum_mm, pct_out_now,
               (warn_svr OR warn_tor)::DOUBLE AS warn
        FROM marts.mart_study__region_1h ORDER BY hour, region_fips
    """).df()
    pairs = con.sql("SELECT * FROM intermediate.int_study__region_neighbors").df()
    con.close()
    regions = sorted(base.region_fips.unique())
    hours = base.hour.unique()
    col = {r: i for i, r in enumerate(regions)}
    out = {"region_fips": np.repeat(regions, len(hours)), "hour": np.tile(hours, len(regions))}
    sources = {"gust_max_ms": ("gust_max_ms", np.nanmax), "cape_max_jkg": ("cape_max_jkg", np.nanmax),
               "precip_max_mm": ("precip_sum_mm", np.nanmax), "pct_out_max": ("pct_out_now", np.nanmax),
               "warn_share": ("warn", np.nanmean)}
    for name, (source, agg) in sources.items():
        grid = base.pivot(index="hour", columns="region_fips", values=source).reindex(columns=regions).to_numpy()
        for kind, flag in (("near", "is_near"), ("up", "is_upwind")):
            values = np.full((len(regions), len(hours)), np.nan)
            for r, group in pairs[pairs[flag]].groupby("region_fips"):
                cols = [col[n] for n in group.neighbor_fips]
                with np.errstate(all="ignore"), warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)     # all-NaN hours stay NaN
                    values[col[r]] = agg(grid[:, cols], axis=1)
            out[f"{kind}_{name}"] = values.ravel()
    result = pd.DataFrame(out)
    cache.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(cache, index=False)
    return result


def check_history(df, features):
    """History features summarize past outages; a row's history must end before the row's own
    year starts, or the model is fed the outcomes it is asked to predict."""
    if set(features) & set(FEATURE_GROUPS["history"]):
        year_start = pd.to_datetime(df["year"].astype(str) + "-01-01")
        if (pd.to_datetime(df["history_end"]) > year_start).any():
            raise ValueError("history features include outages from the row's own year or later")


def label(df, threshold_pct):
    """The target for one threshold, plus which rows are onsets.

    y         peak % of customers out in the block >= threshold
    is_onset  the previous block was known and NOT already an event at this threshold —
              "a new outage", the part that matters for getting crews ready. Rows whose
              previous block is unknown (EAGLE-I down, first block) are neither.
    """
    df = df.copy()
    df["y"] = (df["peak_pct_out"] >= threshold_pct).astype(int)
    df["is_onset"] = df["prev_block_pct_out"].notna() & (df["prev_block_pct_out"] < threshold_pct)
    return df


def add_derived(df):
    """Engineered features (separate from load() so tests can use a synthetic frame)."""
    df = df.copy()
    df["year"] = df["block_start"].dt.year
    df["log_customers"] = np.log10(df["customers"])
    df["wind_x_precip"] = df["gust_max_ms"] * df["precip_sum_mm"]
    df["wind_squared"] = df["gust_max_ms"] ** 2
    df["shear_x_cape"] = df["shear_0_6km_max_ms"] * df["cape_max_jkg"]
    df["wn_wind_x_precip"] = df["wind10_max_ms"] * df["precip_sum_mm"]
    df["wn_wind_squared"] = df["wind10_max_ms"] ** 2
    for col in ["warn_svr", "warn_tor", "warn_wind", "warn_winter"]:
        if col in df:
            df[col] = df[col].astype(int)
    df["wind_x_wet_soil"] = df["gust_max_ms"] * df["precip_prev_72h_mm"]
    return df.reset_index(drop=True)
