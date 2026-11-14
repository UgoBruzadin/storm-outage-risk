"""Load the modeling table and define feature groups.

One row = one region x one 6-hour block, from marts.mart_study__region_6h,
plus the region's resilience history and a few "recent outage" features.

Feature groups are combined by name in benchmark configs:
    "weather+place+history"   -> union of the three groups
    "weather+place-canopy"    -> minus every feature in the "canopy" group
"""
import hashlib
import json
import os
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# STORM_WAREHOUSE points every script at another warehouse, e.g. an archived seven-state build for a check
DB = Path(os.environ.get("STORM_WAREHOUSE", ROOT / "data" / "warehouse.duckdb"))
_SEED = pd.read_csv(ROOT / "dbt" / "seeds" / "study_states.csv", dtype=str)
STATES = dict(zip(_SEED.state_fips, _SEED.state_name, strict=True))      # the study area: "29" -> "Missouri"
STATE_ABBR = dict(zip(_SEED.state_fips, _SEED.state_abbr, strict=True))  # "29" -> "MO"

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


def load(threshold_pct, years, db=DB, pieces=12):
    """Every usable region-block in `years` with features (and the label, if threshold_pct is given).

    Read `pieces` ranges of regions at a time and joined: every column is computed within one region (the window
    functions are per region, the history join is by region), so the pieces join into exactly the table one query
    gives, in the same order, at a fraction of the memory (one query for the whole country's 26M blocks peaked at
    54 GB for a 14 GB frame and took down WSL)."""
    con = duckdb.connect(str(db), read_only=True)
    regions = [r[0] for r in con.sql(
        "SELECT DISTINCT region_fips FROM marts.mart_study__region_6h ORDER BY region_fips").fetchall()]
    starts = regions[::max(1, -(-len(regions) // pieces))]
    parts = [_load_regions(con, years, f"region_fips >= '{lo}'" + (f" AND region_fips < '{hi}'" if hi else ""))
             for lo, hi in zip(starts, [*starts[1:], None], strict=True)]
    con.close()
    df = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
    del parts
    df = add_derived(df, copy=False)              # the frame is ours: no second copy of the whole country
    return label(df, threshold_pct) if threshold_pct is not None else df


def _load_regions(con, years, regions):
    """load()'s query for the regions matching the SQL condition `regions`."""
    return con.sql(f"""
        WITH m AS (
            -- recent-outage features use the full grid (before filtering), so the
            -- first block of a year still sees the last blocks of the previous one
            SELECT
                *,
                lag(peak_pct_out) OVER w                                        AS prev_block_pct_out,
                max(peak_pct_out) OVER (w ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) AS max_pct_out_prev_24h
            FROM marts.mart_study__region_6h
            WHERE {regions}
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


HOURLY_LEADS = (0, 1, 2, 3, 6)
# a new outage must be fresh: no hour at or above the threshold in the FRESH_HOURS before it. A county hovering
# around the line (6%, 4%, 6%) is one outage continuing, not a new one (docs/experiments.md, E25)
FRESH_HOURS = 24


def _hourly_query(threshold_pct, years, lead, onsets_only, states, neg_frac, sample_years):
    """The SQL behind load_hourly (and hourly_counts): the same rows, so counts and rows always agree."""
    if lead not in HOURLY_LEADS:
        raise ValueError(f"lead must be one of {HOURLY_LEADS}")
    others = ", ".join(f"fut_max_pct_{x}, start_pct_{x}" for x in HOURLY_LEADS)
    # the FRESH_HOURS before the window, which starts `lead` hours after the decision
    before = (f"{FRESH_HOURS} PRECEDING AND 1 PRECEDING" if lead == 0
              else f"{FRESH_HOURS - lead} PRECEDING AND {lead - 1} FOLLOWING")
    year_list = ", ".join(str(int(y)) for y in years)
    sampled = [int(y) for y in (sample_years if sample_years is not None else years)] if neg_frac else []
    # A decision is sampled by a hash of its region and hour, not a random draw: the same rows every run, on
    # any machine, whatever order DuckDB scans in, and the same rows at every lead and in every script.
    keep = (f"hash(region_fips || '|' || strftime(hour, '%Y%m%d%H')) % 1000000 < {round(neg_frac * 1_000_000)}"
            if neg_frac else "true")
    is_sampled_year = f"year(hour) IN ({', '.join(map(str, sampled))})" if sampled else "false"
    positive = f"fut_max_pct_{lead} >= {float(threshold_pct)}"
    return f"""
        WITH m AS (
            SELECT *, max(pct_out) OVER (PARTITION BY region_fips ORDER BY hour ROWS BETWEEN {before})
                      AS max_pct_before_window
            FROM marts.mart_study__region_1h
            WHERE year(hour) BETWEEN {min(years) - 1} AND {max(years)}
              {"AND left(region_fips, 2) IN (" + ", ".join(f"'{x}'" for x in states) + ")" if states else ""}
        )
        SELECT * EXCLUDE ({others}, hour, hour_utc, max_pct_before_window),
               hour AS block_start, hour_utc AS block_hour_utc,
               fut_max_pct_{lead} AS fut_max_pct, start_pct_{lead} AS start_pct,
               -- each kept non-outage decision stands for 1 / neg_frac of them, so totals match the full table
               CASE WHEN {is_sampled_year} AND NOT {positive} THEN {1 / neg_frac if neg_frac else 1.0}
                    ELSE 1.0 END AS weight
        FROM m
        -- only region-years EAGLE-I was tracking (mart_study__region_coverage)
        SEMI JOIN marts.mart_study__region_coverage AS c
               ON c.region_fips = m.region_fips AND c.year = year(m.hour) AND c.tracked
        WHERE has_weather
          AND fut_max_pct_{lead} IS NOT NULL
          AND year(hour) IN ({year_list})
          {f"AND start_pct_{lead} < {float(threshold_pct)}" if onsets_only else ""}
          {f"AND coalesce(max_pct_before_window, 0) < {float(threshold_pct)}" if onsets_only else ""}
          AND (NOT {is_sampled_year} OR {positive} OR {keep})
    """


TABLE_CACHE = ROOT / "data" / "cache" / "tables"


def cached(kind, key, build, code_files=(__file__,), db=DB, filters=None):
    """build() once, then read it back: data/cache/tables/<kind>/<hash>.parquet, where the hash covers `key`, the
    warehouse and its modification time (a dbt build invalidates everything) and the source of `code_files` (an
    edit to the code that builds a table invalidates it). STORM_NO_CACHE=1 turns it off. Written to a temporary
    file and renamed, so two scripts building the same table never read a half-written one.
    filters: pyarrow row filters for reading part of a big table (e.g. one state of the whole country's)."""
    if os.environ.get("STORM_NO_CACHE"):
        df = build()
        return df if not filters else pd.read_parquet(_to_buffer(df), filters=filters)
    code = hashlib.sha1(b"".join(Path(f).read_bytes() for f in code_files)).hexdigest()
    stamp = json.dumps({"key": key, "warehouse": str(Path(db).resolve()), "mtime": Path(db).stat().st_mtime,
                        "code": code}, sort_keys=True, default=str)
    path = TABLE_CACHE / kind / f"{hashlib.sha1(stamp.encode()).hexdigest()[:20]}.parquet"
    if path.exists():
        return pd.read_parquet(path, filters=filters)
    df = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    df.to_parquet(tmp, index=False, row_group_size=500_000)       # row groups small enough for filters to skip
    tmp.replace(path)
    path.with_suffix(".json").write_text(stamp)
    return df if not filters else pd.read_parquet(path, filters=filters)


def _to_buffer(df):
    import io
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    return buf


def load_hourly(threshold_pct, years, lead, onsets_only=True, neighbors=True, db=DB, states=None,
                neg_frac=None, sample_years=None, float32=False):
    """Cached (see cached()): the same arguments on the same warehouse and code read the table back from disk."""
    key = {"threshold": threshold_pct, "years": sorted(int(y) for y in years), "lead": lead,
           "onsets_only": onsets_only, "neighbors": neighbors, "states": sorted(states) if states else None,
           "neg_frac": neg_frac, "sample_years": sorted(sample_years) if sample_years is not None else None,
           "float32": float32}
    return cached("hourly", key, lambda: _load_hourly(threshold_pct, years, lead, onsets_only, neighbors, db, states,
                                                      neg_frac, sample_years, float32), db=db)


def _load_hourly(threshold_pct, years, lead, onsets_only=True, neighbors=True, db=DB, states=None,
                 neg_frac=None, sample_years=None, float32=False):
    """The moving-window table (marts.mart_study__region_1h) for one lead: a row is a decision at the
    start of `hour` about the 6 hours starting `lead` hours later. Features use only what had happened
    by `hour`; y = the window's worst hour >= threshold_pct; is_onset = the region was known to be below
    the threshold when the window began. With onsets_only, a row is kept only if no hour in the FRESH_HOURS
    before the window reached the threshold (hours after `hour` only select rows, they are never features).
    Columns are renamed so the 6-hour feature groups apply:
    hour -> block_start (the decision time), hour_utc -> block_hour_utc.
    states: state FIPS codes to keep (default: every study state).

    For tables too big for memory (the whole country, E54):
      neg_frac      in sample_years (default: every year asked for), keep every decision followed by an outage
                    and this share of the others, chosen by a hash of region and hour; `weight` is 1 / neg_frac
                    on the kept others and 1 elsewhere, so weighted totals match the full table. Pass the
                    weights to fit(); never sample a year that is scored.
      float32       store numeric inputs as 32-bit floats after the derived features are computed in 64-bit
                    (XGBoost works in 32-bit floats anyway, so its splits don't change)."""
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(_hourly_query(threshold_pct, years, lead, onsets_only, states, neg_frac, sample_years)
                 + " ORDER BY region_fips, hour").df()
    con.close()
    if neighbors:
        nb = neighbor_features(db=db, years=years, states=states).rename(columns={"hour": "block_start"})
        df = df.merge(nb, on=["region_fips", "block_start"], how="left")
        del nb
    df = add_derived(df, copy=False)
    df["y"] = (df["fut_max_pct"] >= threshold_pct).astype(int)
    df["is_onset"] = df["start_pct"].notna() & (df["start_pct"] < threshold_pct)
    return shrink(df) if float32 else df


def hourly_counts(threshold_pct, years, lead, by, onsets_only=True, db=DB, states=None):
    """Decisions and outages per group of `by` columns over the FULL table (no sampling): what a rate table
    such as the warnings + outlook baseline is fitted on, so it stays exact when the model trains on a sample.
    Returns `by` columns + y (0/1) + weight (how many decisions), ready for RateBaseline.fit(..., sample_weight)."""
    cols = ", ".join(by)
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        SELECT {cols}, (fut_max_pct >= {float(threshold_pct)})::INT AS y, count(*)::DOUBLE AS weight
        FROM ({_hourly_query(threshold_pct, years, lead, onsets_only, states, None, None)})
        GROUP BY ALL ORDER BY ALL
    """).df()
    con.close()
    return add_warning_ints(df)


# Training keeps every decision followed by an outage and this share of the others, weighted 1 / NEG_FRAC
# (load_hourly). E54: 0.1 gave 3.53x against 3.54x for the full table on five states. A scored year is never sampled.
NEG_FRAC = 0.1


def sampled_years(threshold_pct, years, lead, neg_frac=NEG_FRAC, add=None, **kwargs):
    """Training rows for `years`, loaded and sampled one year at a time and stacked, so the whole country's years
    are never in memory unsampled. add(df, year) -> df joins more columns onto each year's rows (window weather)
    before they are stacked. kwargs go to load_hourly (onsets_only, neighbors, states)."""
    parts = []
    for y in years:
        df = load_hourly(threshold_pct, [y], lead, neg_frac=neg_frac, float32=True, **kwargs)
        if add is not None:
            df = add(df, y)
        parts.append(shrink(df))
        print(f"training rows {y}: {len(df):,} kept, standing for {df.weight.sum():,.0f}", flush=True)
        del df
    return pd.concat(parts, ignore_index=True)


def state_rows(threshold_pct, year, lead, **kwargs):
    """Every decision of one year (never sampled: it is scored), one state at a time: yields (state, rows).
    kwargs go to load_hourly (onsets_only, neighbors)."""
    for s in warehouse_states():
        df = load_hourly(threshold_pct, [year], lead, states=[s], float32=True, **kwargs)
        if len(df):
            yield s, df


def warehouse_states(db=DB):
    """The state FIPS codes the warehouse has rows for (an archived build can hold fewer than the seed lists)."""
    con = duckdb.connect(str(db), read_only=True)
    states = [r[0] for r in con.sql(
        "SELECT DISTINCT left(region_fips, 2) FROM marts.mart_study__region_1h ORDER BY 1").fetchall()]
    con.close()
    return states


def shrink(df):
    """64-bit floats -> 32-bit, in place of a copy (half the memory)."""
    for c in df.columns[df.dtypes == "float64"]:
        df[c] = df[c].astype("float32")
    return df


NEIGHBOR_CACHE = ROOT / "data" / "cache" / "neighbors_1h"


def _neighbor_cache_dir(db, cache):
    """One cache per warehouse: the default warehouse uses `cache`, any other one a folder named after it."""
    db = Path(db)
    return cache if db.resolve() == (ROOT / "data" / "warehouse.duckdb").resolve() else cache.with_name(
        f"{cache.name}_{db.stem}")


def _neighbor_cache_valid(folder, db):
    """The cache records the warehouse it was built from; a rebuilt warehouse (newer file) invalidates it."""
    stamp = folder / "_built_from.json"
    if not stamp.exists():
        return False
    built = json.loads(stamp.read_text())
    return built.get("warehouse_mtime") == Path(db).stat().st_mtime


def neighbor_features(db=DB, cache=NEIGHBOR_CACHE, years=None, states=None):
    """For every region and hour, its neighbours' known-by-then features (mart_study__region_1h):
    the strongest gust and CAPE and the most rain in the past 6 hours, the worst outage in the
    hour before, and the share with a severe thunderstorm or tornado warning in force; near_* =
    within 100 km, up_* = upwind (intermediate.int_study__region_neighbors). Computed as
    hour x region arrays (a SQL join would be ~400M rows).

    Every feature is a cross-section of one hour, so the cache is built and stored a year at a time
    (<cache>/<year>.parquet, 32-bit floats): the whole country never has to be in memory at once, and the
    numbers are the same as building it in one go. It is rebuilt automatically when the warehouse changes.
    years / states: return only these years (default: all) and these states' regions (default: all)."""
    folder = _neighbor_cache_dir(db, cache)
    if not _neighbor_cache_valid(folder, db):
        _build_neighbor_cache(db, folder)
    files = sorted(folder.glob("*.parquet"))
    if years is not None:
        wanted = {int(y) for y in years}
        files = [f for f in files if int(f.stem) in wanted]
    filters = None
    if states:
        con = duckdb.connect(str(db), read_only=True)
        regions = con.sql("SELECT DISTINCT region_fips FROM marts.mart_study__region_1h WHERE left(region_fips, 2) IN ("
                          + ", ".join(f"'{s}'" for s in states) + ")").df().region_fips.tolist()
        con.close()
        filters = [("region_fips", "in", regions)]
    parts = [pd.read_parquet(f, filters=filters) for f in files]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["region_fips", "hour"])


def _build_neighbor_cache(db, folder):
    con = duckdb.connect(str(db), read_only=True)
    pairs = con.sql("SELECT * FROM intermediate.int_study__region_neighbors").df()
    year_list = [r[0] for r in con.sql(
        "SELECT DISTINCT year(hour) FROM marts.mart_study__region_1h ORDER BY 1").fetchall()]
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.parquet"):
        old.unlink()
    (folder / "_built_from.json").unlink(missing_ok=True)
    sources = {"gust_max_ms": ("gust_max_ms", np.nanmax), "cape_max_jkg": ("cape_max_jkg", np.nanmax),
               "precip_max_mm": ("precip_sum_mm", np.nanmax), "pct_out_max": ("pct_out_now", np.nanmax),
               "warn_share": ("warn", np.nanmean)}
    for year in year_list:
        base = con.sql(f"""
            SELECT region_fips, hour, gust_max_ms, cape_max_jkg, precip_sum_mm, pct_out_now,
                   (warn_svr OR warn_tor)::DOUBLE AS warn
            FROM marts.mart_study__region_1h WHERE year(hour) = {int(year)} ORDER BY hour, region_fips
        """).df()
        regions = sorted(base.region_fips.unique())
        hours = base.hour.unique()
        col = {r: i for i, r in enumerate(regions)}
        out = {"region_fips": np.repeat(regions, len(hours)), "hour": np.tile(hours, len(regions))}
        for name, (source, agg) in sources.items():
            grid = base.pivot(index="hour", columns="region_fips", values=source).reindex(columns=regions).to_numpy()
            for kind, flag in (("near", "is_near"), ("up", "is_upwind")):
                values = np.full((len(regions), len(hours)), np.nan)
                for r, group in pairs[pairs[flag]].groupby("region_fips"):
                    if r not in col:
                        continue
                    cols = [col[n] for n in group.neighbor_fips if n in col]
                    if not cols:
                        continue
                    with np.errstate(all="ignore"), warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)     # all-NaN hours stay NaN
                        values[col[r]] = agg(grid[:, cols], axis=1)
                out[f"{kind}_{name}"] = values.ravel().astype("float32")
            del grid
        pd.DataFrame(out).to_parquet(folder / f"{year}.parquet", index=False)
        print(f"neighbour cache {year}: {len(regions)} regions x {len(hours)} hours", flush=True)
        del base, out
    con.close()
    (folder / "_built_from.json").write_text(json.dumps(
        {"warehouse": str(db), "warehouse_mtime": Path(db).stat().st_mtime}))


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


def add_derived(df, copy=True):
    """Engineered features (separate from load() so tests can use a synthetic frame).
    copy=False adds them to `df` itself (for a frame the caller owns, to save memory)."""
    if copy:
        df = df.copy()
    df["year"] = df["block_start"].dt.year
    df["log_customers"] = np.log10(df["customers"])
    df["wind_x_precip"] = df["gust_max_ms"] * df["precip_sum_mm"]
    df["wind_squared"] = df["gust_max_ms"] ** 2
    df["shear_x_cape"] = df["shear_0_6km_max_ms"] * df["cape_max_jkg"]
    df["wn_wind_x_precip"] = df["wind10_max_ms"] * df["precip_sum_mm"]
    df["wn_wind_squared"] = df["wind10_max_ms"] ** 2
    add_warning_ints(df)
    df["wind_x_wet_soil"] = df["gust_max_ms"] * df["precip_prev_72h_mm"]
    return df.reset_index(drop=True)


def add_warning_ints(df):
    """Warnings in force as 0/1 integers (DuckDB returns booleans), the same in rows and in hourly_counts."""
    for col in ["warn_svr", "warn_tor", "warn_wind", "warn_winter"]:
        if col in df:
            df[col] = df[col].astype(int)
    return df
