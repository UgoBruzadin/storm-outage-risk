"""A two-state copy of the project for `pixi run pipeline --smoke`: every step runs on Missouri + Illinois with a few
trees, in minutes, without touching the real results, caches or dashboard data.

data/smoke/root/ mirrors the repository: the code's inputs are links to the real ones (raw data, the forecasts split
by state, every top-level folder but data/ and ml/), and it gets its own:
  data/warehouse.duckdb       every warehouse table cut to the two states (rebuilt when the real one is newer); the
                              staging views the scripts read become tables
  dbt/seeds/study_states.csv  the two states
  data/cache, data/app, ml/results   empty to start, written by the smoke run
The pipeline points every script at it with STORM_ROOT (ml/data.py) and caps every model at 5 trees (STORM_SMOKE).

Usage: pixi run pipeline --smoke   (calls prepare(); `python -m ml.smoke` only builds the tree)
"""
import shutil
from pathlib import Path

import duckdb
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "data" / "smoke" / "root"
STATES = ["17", "29"]                                       # Illinois, Missouri
VIEWS = ["stg_noaa__storm_events", "stg_noaa__zone_county", "stg_nws__warnings", "stg_spc__day1_outlooks"]
SKIP = {"data", "ml", ".git", ".pixi", "node_modules", "__pycache__"}


def link(target, at):
    if at.is_symlink() or at.exists():
        return
    at.parent.mkdir(parents=True, exist_ok=True)
    at.symlink_to(target)


def warehouse(src, dst):
    """Every table of `src` cut to STATES (by region_fips, and neighbor_fips where there is one); the VIEWS copied
    whole as tables (they read raw files by paths relative to the repository)."""
    tmp = dst.with_suffix(".tmp.duckdb")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    con.execute(f"ATTACH '{src}' AS src (READ_ONLY)")
    tables = con.sql("""SELECT table_schema, table_name, table_type FROM information_schema.tables
                        WHERE table_catalog = 'src'""").fetchall()
    states = ", ".join(f"'{s}'" for s in STATES)
    for schema, name, kind in tables:
        if kind != "BASE TABLE" and name not in VIEWS:
            continue
        cols = {r[0] for r in con.sql(f"""SELECT column_name FROM information_schema.columns
                                         WHERE table_catalog = 'src' AND table_schema = '{schema}'
                                           AND table_name = '{name}'""").fetchall()}
        where = [f"left({c}, 2) IN ({states})" for c in ("region_fips", "neighbor_fips") if c in cols]
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        con.execute(f"CREATE TABLE {schema}.{name} AS SELECT * FROM src.{schema}.{name}"
                    + (f" WHERE {' AND '.join(where)}" if where else ""))
        print(f"smoke warehouse: {schema}.{name}", flush=True)
    con.close()
    tmp.replace(dst)


def prepare():
    """Build (or refresh) the smoke tree and return its root."""
    for entry in REPO.iterdir():
        if entry.name not in SKIP and entry.name != "dbt":
            link(entry, ROOT / entry.name)
    for entry in (REPO / "dbt").iterdir():
        if entry.name != "seeds":
            link(entry, ROOT / "dbt" / entry.name)
    for entry in (REPO / "dbt" / "seeds").iterdir():
        if entry.name != "study_states.csv":
            link(entry, ROOT / "dbt" / "seeds" / entry.name)
    seed = pd.read_csv(REPO / "dbt" / "seeds" / "study_states.csv", dtype=str)
    seed[seed.state_fips.isin(STATES)].to_csv(ROOT / "dbt" / "seeds" / "study_states.csv", index=False)
    for entry in (REPO / "ml").iterdir():
        if entry.name not in ("results", "__pycache__"):
            link(entry, ROOT / "ml" / entry.name)
    link(REPO / "data" / "raw", ROOT / "data" / "raw")
    link(REPO / "data" / "cache" / "hrrr_fcst_by_state", ROOT / "data" / "cache" / "hrrr_fcst_by_state")
    for d in ("ml/results", "data/app", "data/cache", "data/pipeline_logs"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    src, dst = REPO / "data" / "warehouse.duckdb", ROOT / "data" / "warehouse.duckdb"
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        warehouse(src, dst)
    return ROOT


def reset():
    """Remove the smoke run's outputs and caches (the warehouse copy stays)."""
    for d in ("ml/results", "data/app", "data/cache/tables", "data/site_preview", "data/pipeline_logs"):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    for d in ("ml/results", "data/app", "data/pipeline_logs"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(prepare())
