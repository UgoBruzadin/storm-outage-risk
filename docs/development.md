# Development guide

How to run, extend and debug the project.

## The whole pipeline, in order

```bash
# 1. raw data (each step skips files it already has)
pixi run fetch-noaa           # KSTL airport weather            (minutes)
pixi run fetch-counties       # Census county shapes            (seconds)
pixi run fetch-weather        # HRRR per region via Open-Meteo  (rate-limited: run in the background)
pixi run fetch-tree-canopy    # canopy % per region             (~3 min)
pixi run fetch-acs            # Census housing tables           (seconds)
pixi run fetch-storm-events   # NOAA storm reports              (~1 min)
# EAGLE-I outages: manual download, see data/README.md

# 2. warehouse
pixi run build                # dbt deps + dbt build

# 3. models (see ml/README.md)
pixi run train                # quick benchmark: baselines vs model families
pixi run benchmark ml/benchmarks/full.yaml   # grid search + ablations (hours)
pixi run mlflow-ui            # browse and compare runs at http://127.0.0.1:5000

# 4. dashboard
pixi run export-app           # the benchmark config's `final:` model -> data/app/
pixi run app                  # http://localhost:8501
docker compose up --build     # the same app in a container

# 5. publish (private by default)
pixi run publish-data         # data/app -> Hugging Face dataset
pixi run deploy-space         # app -> Hugging Face Space
```

Long downloads run detached so closing the terminal doesn't stop them:
`nohup scripts/queue_weather.sh 2018 2019 > data/raw/weather/queue.log 2>&1 &`
(the queue runs downloads one after another, since they share Open-Meteo's daily quota).

## Frequent commands

| Command | Does |
|---|---|
| `pixi run dbt build --select <model>+` | rebuild one model and everything downstream |
| `pixi run dbt test --select <model>` | just the tests |
| `pixi run dbt docs generate && pixi run dbt docs serve` | browsable docs + lineage graph |
| `pixi run benchmark <config> --dry-run` / `--resume` | list a benchmark's runs / finish an interrupted one |
| `pixi run ruff check .` / `pixi run pytest -q` | lint / tests (CI runs both) |
| `pixi add <pkg>` / `pixi add --pypi <pkg>` | add a dependency |
| `pixi task list` | every task |

Notebooks use the kernel `.pixi/envs/default/bin/python` (the `app` and `ci` environments
are minimal and lack geopandas, dbt and the ML libraries).

## Conventions

1. **Tables are never edited by hand.** The SQL is the source of truth; change it and rebuild.
2. **Every model has tests** in its `_*.yml` — at least a unique, non-null key.
3. **Join keys are checked for uniqueness** on the "one" side before joining.
4. **Surprising numbers are investigated before moving on**, and recorded in [data-notes.md](data-notes.md).
5. **Every feature passes the leakage check:** would it be known at the start of the block?
6. **NULL means unknown.** It becomes 0 only when 0 is known to be true; `least()` and
   `greatest()` skip NULLs, so they are never used on nullable values without an `IS NULL` check.
7. **The study area is defined once**, in `dbt/seeds/study_states.csv`, for both dbt and ingest.

## Adding a data source

1. `ingest/fetch_<source>.py` downloads into `data/raw/<source>/`, skips existing files, and gets a `fetch-<source>` task.
2. Declare it in `dbt/models/staging/_sources.yml` (no `{}` in `external_location`: read as text and cast in staging).
3. `stg_<source>__<thing>.sql` renames, casts and decodes missing-value codes — nothing else.
4. Tests go in `_staging.yml`; intermediate models use it via `{{ ref() }}`.
5. Quirks go in `data-notes.md`, choices in `decisions.md`, every experiment and its result in `experiments.md`.

## Editing the site's text

Every word on the story page is in `site/text.yaml`, in page order. Edit, save, and refresh: the page reads the file
directly. To preview locally, serve the folder (`python3 -m http.server -d site`, then http://localhost:8000).
Placeholders such as `{ratio}` are numbers filled in from `site/data/story.json`; a comment above each says what it
holds. `tests/test_site.py` fails if the page asks for a key the file doesn't have. The link-preview text (title,
description) stays in the `<head>` of `site/index.html`, because link previews are read without running the page.

## Troubleshooting

- **"Could not set lock"** — something else has `data/warehouse.duckdb` open (the DuckDB UI
  or a notebook kernel). Close it and retry.
- **A dbt test fails** — `pixi run dbt test --select <model> --store-failures`, then query the failing rows.
- **A count is off** — run the checks in pipeline order; the first wrong table is where the bug is.
- **Open-Meteo "rate limited"** — expected on the free tier; the fetch script waits and resumes.
- **Docker "cannot connect to the daemon"** — start Docker Desktop.
