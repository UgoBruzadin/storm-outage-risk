# Working on this project

A guide for future me: how to pick this up after a break and keep going without help.

## Every session

```bash
cd ~/Documents/GitHub/storm-outage-risk
git status                 # what changed since last time?
git pull                   # if you work from more than one machine
pixi run build             # rebuild the warehouse if SQL or raw data changed
```

Then check [roadmap.md](roadmap.md) for the next unticked box.

## Commands

| Command | Does |
|---|---|
| `pixi install` | create/update the environment from `pixi.toml` |
| `pixi run build` | rebuild `data/warehouse.duckdb` and print the check numbers |
| `pixi run fetch-noaa` | download NOAA weather (skips files you already have) |
| `pixi add <package>` | add a conda package (`pixi add --pypi <pkg>` for PyPI-only ones) |
| `pixi task list` | list all tasks |
| `~/.duckdb/cli/latest/duckdb -ui data/warehouse.duckdb` | DuckDB notebook UI in the browser |

Notebooks: pick the kernel `.pixi/envs/default/bin/python`.

## Git habits

- **Commit when something works**, with a message that says *why*: `git add -A && git commit -m "Merge St. Louis regions: County filed under City 2020–2024"`.
- **One branch per milestone**: `git switch -c m1-dbt` → work → merge into `main` when the checks pass.
- Before committing, `git status`: no data files, no `.duckdb`, no `.env` should appear. If one does, fix `.gitignore` first.
- Undo uncommitted changes to a file: `git restore <file>`.

## House rules for the pipeline

1. **Never edit tables by hand.** Change the SQL, rebuild. The SQL is the source of truth.
2. **Every table gets a check** — expected row count or a uniqueness rule — written next to it (in dbt: a test).
3. **Before every join, check the key is unique** on the "one" side: `count(*) = count(DISTINCT key)`.
4. **When a number surprises you, investigate before moving on**, then write it down in [data-notes.md](data-notes.md).
5. **Leakage check for every feature:** "would I know this at the start of hour *t*?"

## Adding a new data source (recipe)

1. `ingest/fetch_<source>.py` — download into `data/raw/<source>/`, skip files that already exist.
2. Load it as text first (`all_varchar = true`) into a `raw` table; look at it (`LIMIT 10`, `GROUP BY` counts).
3. Clean it into a `stg` table: types, missing-value codes, one row per key.
4. Check: row counts, uniqueness, min/max dates, NULL counts.
5. Join it into the grid with a `LEFT JOIN`; confirm the grid's row count didn't change.
6. Note any quirks in `data-notes.md`, the choice in `decisions.md`.

## Where the data lives

`data/raw` is a **symlink** to the old sandbox (`../Weather-Analysis-STL/outage-predictor/data/raw`) so the 11 GB isn't duplicated. To make this repo self-contained, move the files and replace the link:

```bash
rm data/raw
mv ../Weather-Analysis-STL/outage-predictor/data/raw data/raw
```

## When stuck

- Error mentions **lock** → something else has the database open (UI, notebook kernel, a build).
- A count is off → run the checks in order; the first table whose count is wrong is where the bug is.
- Asking an AI or a forum: paste the query, the full error, and what you expected — and say which DuckDB version (`SELECT version()`).
