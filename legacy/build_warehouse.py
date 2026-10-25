"""Rebuild data/warehouse.duckdb from the raw files by running the SQL pipeline in order.

Usage (from anywhere):  pixi run build-legacy

Superseded by dbt (pixi run build); kept for the St. Louis hourly notebook.
"""
import os
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent   # repo root (this file lives in legacy/)
DB_PATH = ROOT / "data" / "warehouse.duckdb"
SQL_FILES = [
    ROOT / "legacy" / "sql" / "merge_all.sql",    # St. Louis metro: hourly outages + weather
    ROOT / "legacy" / "sql" / "build_mo_il.sql",  # every Missouri/Illinois region (needs merge_all first)
]


def main():
    os.chdir(ROOT)  # the SQL reads files with paths relative to the repo root
    con = duckdb.connect(str(DB_PATH))
    for sql_file in SQL_FILES:
        start = time.time()
        # Each file ends with a check query; reading its result also lets
        # DuckDB 2.x finish the statement before the next file runs.
        check = con.execute(sql_file.read_text()).df()
        print(f"\n{sql_file.relative_to(ROOT)}: done in {time.time() - start:.0f}s")
        print(check.to_string(index=False))
    print()
    print(con.sql("""
        SELECT schema_name, table_name, estimated_size AS approx_rows
        FROM duckdb_tables()
        ORDER BY schema_name, table_name
    """))
    con.close()


if __name__ == "__main__":
    main()
