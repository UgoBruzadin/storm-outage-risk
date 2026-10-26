# Working on this project

A guide for future me: how to pick this up after a break and keep going without help.

## Every session

```bash
cd ~/Documents/GitHub/storm-outage-risk
git status && git pull        # what changed? anything from another machine?
pixi run build                # dbt: rebuild every table + run every test (~30 s)
```

Then check [roadmap.md](roadmap.md) for the next unticked box.

## The whole pipeline, in order

```bash
# 1. raw data (each step skips files it already has)
pixi run fetch-noaa           # KSTL airport weather            (minutes)
pixi run fetch-counties       # Census county shapes            (seconds)
pixi run fetch-weather        # HRRR per region via Open-Meteo  (~a day: rate-limited; run in the background)
pixi run fetch-tree-canopy    # canopy % per region             (~3 min)
pixi run fetch-acs            # Census housing tables           (seconds)
pixi run fetch-storm-events   # NOAA storm reports              (~1 min)
# EAGLE-I outages: manual download, see data/README.md

# 2. warehouse
pixi run build                # dbt deps + dbt build

# 3. model (see ml/README.md)
pixi run train                # the quick benchmark: baselines vs model families (minutes)
pixi run benchmark ml/benchmarks/full.yaml   # grid search + ablations (~30-60 min)
pixi run mlflow-ui            # browse/compare runs at http://127.0.0.1:5000

# 4. dashboard
pixi run export-app           # the benchmark config's `final:` model -> data/app/
pixi run app                  # http://localhost:8501
docker compose up --build     # the same app in a container (needs Docker Desktop running)

# 5. publish (asks nothing — check what you're uploading first; private by default)
pixi run publish-data         # data/app -> Hugging Face dataset
pixi run deploy-space         # app -> Hugging Face Space
```

Long downloads: run them detached so closing the terminal doesn't stop them,
e.g. `nohup pixi run fetch-weather > data/raw/weather/fetch.log 2>&1 &`.

## Commands you'll use a lot

| Command | Does |
|---|---|
| `pixi run dbt build --select <model>+` | rebuild one model and everything downstream |
| `pixi run dbt test --select <model>` | just the tests |
| `pixi run dbt docs generate && pixi run dbt docs serve` | browsable docs + lineage graph |
| `pixi run ruff check .` / `pixi run pytest -q` | lint / tests (CI runs both) |
| `pixi add <pkg>` / `pixi add --pypi <pkg>` | add a dependency |
| `pixi task list` | every task |
| `~/.duckdb/cli/latest/duckdb -ui data/warehouse.duckdb` | DuckDB notebook UI |

Notebooks: pick the kernel `.pixi/envs/default/bin/python`.

## Git habits

- **Commit when something works**, with a message that says *why*.
- **One branch per piece of work** (`git switch -c <name>`), merge into `main` when CI is green.
- Before committing, `git status`: no data files, no `.duckdb`, no `.env`. If one shows up, fix `.gitignore` first.
- Undo uncommitted changes to a file: `git restore <file>`.

## House rules for the pipeline

1. **Never edit tables by hand.** Change the SQL, rebuild. The SQL is the source of truth.
2. **Every model gets tests** in its `_*.yml` — at least the key is unique and not null.
3. **Before every join, check the key is unique** on the "one" side.
4. **When a number surprises you, investigate before moving on** — then write it in [data-notes.md](data-notes.md). Every bug so far was found this way.
5. **Leakage check for every feature:** "would I know this at the start of the block?"
6. **NULL means unknown.** Only turn it into 0 when you know it's 0, and never trust `least()`/`greatest()` with NULLs.

## Adding a new data source (recipe)

1. `ingest/fetch_<source>.py` — download into `data/raw/<source>/`, skip existing files; add a `fetch-<source>` task.
2. Declare it in `dbt/models/staging/_sources.yml` (read as text if it needs `types`; no `{}` there).
3. `stg_<source>__<thing>.sql`: rename, cast, decode missing-value codes — nothing else.
4. Tests in `_staging.yml`; then use it in an intermediate model with `{{ ref() }}`.
5. Quirks → `data-notes.md`, choices → `decisions.md`.

## Where the data lives

`data/raw` is a **symlink** to the old sandbox (`../Weather-Analysis-STL/outage-predictor/data/raw`), and
everything downloaded since went there too. To make this repo self-contained, move the files and replace the link:

```bash
rm data/raw
mv ../Weather-Analysis-STL/outage-predictor/data/raw data/raw
```

## When stuck

- **"Could not set lock"** → something else has `data/warehouse.duckdb` open (the DuckDB UI, a notebook kernel,
  MLflow is fine). Close it and retry.
- **A dbt test fails** → `pixi run dbt test --select <model> --store-failures`, then query the failing rows.
- **A count is off** → run the checks in order; the first wrong table is where the bug is.
- **Open-Meteo "rate limited"** → normal; the fetch script waits and resumes.
- **Docker "cannot connect to the daemon"** → start Docker Desktop.
- Asking an AI or a forum: paste the query, the full error, what you expected, and versions (`pixi list`).
