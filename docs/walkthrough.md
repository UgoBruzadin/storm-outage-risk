# Walkthrough: owning this project

How to know this project well enough to present it, defend it, and extend it alone.
Read top to bottom; the sections are in priority order. Each one ends with something to
**do yourself** — reading isn't owning; reproducing a number or making a call is.

---

## 1. The pitch (know this cold)

**30 seconds:**
> I predict which Missouri and Illinois counties will lose power in the next 6 hours,
> from storm forecasts plus what each place is like. I replicated a published approach
> (weathernext-outage-forecasting), then fixed its evaluation: it scores with a random
> split, which lets one storm leak into both training and test. Under honest splits,
> and scoring only *new* outages, the model flags the riskiest 1% of calm county-blocks,
> and 12% of those become ≥5% outages — 24× the base rate.

**2 minutes** adds: the data (11 GB of DOE outage snapshots, NOAA weather, tree canopy,
Census), the pipeline (dbt on DuckDB with 50+ tests), the three biggest data traps you
found, the main result, and one honest limitation (section 7).

**Do it:** say both versions out loud, timed. Rewrite them in your own words — if a
phrase above isn't how you'd say it, change it.

---

## 2. The problem framing — the decisions an interviewer will probe

| Decision | What we chose | Why | Alternative you should be able to discuss |
|---|---|---|---|
| Unit | region × 6-hour block | matches crew planning; smooths 15-min noise; same as weathernext | hourly (noisier), daily (too coarse for crews) |
| Label | peak % customers out ≥ 1 / 5 / 10% | % makes counties comparable; several sizes because "outage" isn't one thing | raw counts (dominated by big counties), regression on % out |
| Prediction moment | start of the block | weather for the block + outages up to the previous block are known | — |
| **Onsets** | also score blocks where the previous block *wasn't* already an event | outages persist; all-block scores reward "it's out, it stays out" | — this is your strongest framing choice; know why it matters |
| Area | 216 MO + IL regions | place features need many places; 7 St. Louis counties make canopy a region ID | national (more data, more heterogeneity) |

**Do it:** for each row, write one sentence: "if I had chosen the alternative, what
would change?" Then decide whether you'd still choose what we chose. If not, that's a
real change to make — it's your project.

---

## 3. The data and its traps (your best interview stories)

Interviewers remember *how you found a problem* more than the model. Pick three of these
and be able to tell each in under a minute: symptom → investigation → fix → test that
guards it. All are in [data-notes.md](data-notes.md).

1. **Missing rows mean zero — except when they don't.** EAGLE-I only records counties
   with outages. No row = 0… unless EAGLE-I itself was down. Fix: a national
   "heartbeat" — if *no county in the country* has a row, the system was down.
2. **St. Louis County vanished in 2022–2024.** Its outages were filed under St. Louis
   City's FIPS code. Symptom: a county of 594k customers with zero outages. Fix: merge
   them into one region. Cost: one fewer region, honest numbers.
3. **`least(100, NULL)` = 100.** Blank counts became "100% out", creating tens of
   thousands of fake events. Found because a yearly count looked absurd; guarded by a
   dbt regression test (`dbt/tests/assert_pct_null_when_peak_null.sql`).
4. **Farmland with 45% tree canopy.** The raster's nodata tag was 0, a real value, so
   every treeless pixel was dropped. Found by sanity-checking against known places
   (Champaign, IL should be ~2%).
5. **Coverage grows over time.** EAGLE-I tracked fewer utilities before 2019, so early
   years look calm. Training starts in 2020.

**Do it:** open the DuckDB UI (`~/.duckdb/cli/latest/duckdb -ui data/warehouse.duckdb`,
close it before `pixi run build`) and reproduce trap 2 yourself: query
`staging.stg_eaglei__outages` for fips 29189 and 29510 by year. Seeing it in your own
query is different from reading it here.

---

## 4. Leakage and validation (where most projects fail)

Know these three splits and *why* the scores differ:

| Split | Question it answers | Typical onset PR-AUC (≥5%) |
|---|---|---|
| `time` 2024 → 2025 | can it predict the future? | ~0.08 |
| `county` (held-out regions) | can it predict a place it never saw? | ~0.10 |
| `random` (weathernext) | — mostly: can it recognise a storm it already saw next door | inflated |

Leakage guards you should be able to point at:
- History features use 2020–2023 only; `ml/data.py` asserts it ends before the train year.
- Storm Events reports are never features (written after the fact).
- "Recent" features use only *previous* blocks (`lag`, `ROWS ... 1 PRECEDING`).
- KSTL weather is shifted +9 min so a :51 report labels the *next* hour (legacy pipeline).

**The limitation to raise yourself, before they do:** the HRRR weather comes from
Open-Meteo's archive, which stitches the *first hours* of each model run. That's close
to observed weather — a near-perfect 0–6 h forecast. A real 24–48 h forecast is worse,
so these scores are an **upper bound** for crew planning a day ahead. The fix is on the
roadmap (Open-Meteo's archived longer-lead forecasts, 2024+).

**Do it:** in `ml/splits.py`, read `make_splits`. Then read `tests/test_ml.py` — the
tests prove the splits don't leak. Run `pixi run pytest -q tests/test_ml.py` and break a
split on purpose (e.g. make `county` reuse a region) to watch the test fail.

---

## 5. Metrics (be fluent — this is where data scientists get grilled)

- **Why not accuracy?** ≥5% outages are ~0.5–1% of blocks. Predicting "never" is 99% accurate.
- **Why PR-AUC over ROC-AUC?** ROC-AUC counts true negatives, which are almost everything
  here, so it looks good easily (0.9 sounds great; it isn't). PR-AUC focuses on the rare class.
- **What's a good PR-AUC?** Relative to the event rate — no skill scores *the event
  rate*. Hence **lift** = PR-AUC ÷ event rate. 0.084 at a 0.5% rate is 16×.
- **precision / recall @ top 1%:** the operational view — "if a utility watches the
  riskiest 1% of county-blocks, how often is it right, and how much does it catch?"
- **Baselines:** `prior` (event rate) and `climatology` (county × month rate). Climatology
  barely beats chance → the skill comes from the weather, not from "some counties are
  always bad".
- **Calibration** (Brier, log loss): are probabilities trustworthy as probabilities?
  Not checked visually yet — a good thing to add yourself (roadmap).

**Do it:** compute one number by hand. In Python, load
`ml/results/benchmark_quick.csv`, pick one row, and check `onset_pr_auc_lift ==
onset_pr_auc / onset_event_rate`. Then explain to yourself why the lift *grows* with the
outage size (1% → 10%) while the PR-AUC *shrinks*.

---

## 6. Results — what you can and can't claim

Claims the evidence supports (from `ml/results/leaderboard_*.md`):
1. Weather alone predicts new outages 5–10× better than chance.
2. Place + history features add 25–45% on every split and size.
3. Bigger outages are more predictable *relative to chance* (7× → 21×): they're weather-driven.
4. Model family barely matters (LightGBM ≈ XGBoost ≈ HGB); features matter.
5. Random splits overstate skill — the weathernext critique.

Claims it does **not** support:
- "Trees cause outages." Canopy's effect is small and inconsistent, and county-wide canopy
  is confounded with rurality and **which utility** serves the area (co-ops vs. Ameren).
  A null-ish result, honestly reported, is a strength in an interview.
- Anything below county level — there's no sub-county outage data to test it.

**Do it:** open `ml/results/leaderboard_onsets.md`. Find the rows that compare
`weather+place` with `weather+place-canopy`. Write two sentences on what canopy does, in
your own words, with the numbers. That's your answer when asked "so do trees matter?"

---

## 7. Engineering — be able to draw it on a whiteboard

```
ingest/ (Python)          dbt/ (SQL on DuckDB)                     ml/ (Python)              app/
EAGLE-I, HRRR,     ──►  staging → intermediate → marts   ──►  benchmark.py (MLflow)  ──►  export ─► Streamlit
canopy, ACS,             54 tests; region_fips / block_6h        YAML configs, registry      (Docker, HF Space)
Storm Events             macros; 3.5M-row modeling table         onsets, 3 splits
```

Why each tool (one line each — have these ready):
- **DuckDB:** 11 GB of CSVs in seconds on a laptop; no server.
- **dbt:** every transformation is versioned SQL with tests; the lineage graph documents itself.
- **pixi:** one lock file, three environments (full / app / ci) — reproducible, small Docker image.
- **MLflow:** every run logged with params, metrics and git commit.
- **App reads precomputed files only:** fast, free to host, can't break when model code changes.

**Do it:** `pixi run dbt docs generate && pixi run dbt docs serve`, open the lineage
graph, and trace `mart_mo_il__region_6h` back to its raw sources. Then explain each model
in one sentence without looking at its SQL. Where you can't, read that model.

---

## 8. Questions you'll get — practise answers

1. *Why should a utility trust this?* (calibration, precision@top1%, the baselines)
2. *What would you do with more time?* (longer-lead forecasts, more years, utility
   territories, sub-county data from outage maps)
3. *What was the hardest bug?* (pick from section 3)
4. *How did you avoid leakage?* (section 4)
5. *Why not deep learning?* (600k rows of tabular data; trees are the strong baseline;
   the limit is the features, not the model — the families tie)
6. *What surprised you?* (persistence dominates all-block scores; canopy's weak effect)
7. *How would this run in production?* (scheduled ingest + dbt build, forecast weather
   instead of archive weather, monitoring calibration drift, alerting on the top 1%)

---

## How to work from here — taking ownership

The project was built fast with an AI doing most of the typing. To make it yours:

1. **Do every "Do it" above** (a few hours in total). Keep notes on anything you'd change.
2. **Make the next decision yourself.** When the grid search finishes, read the
   leaderboard and choose the `final:` model in `ml/benchmarks/quick.yaml`. Write down
   why. That choice — and its justification — is yours.
3. **Write the next experiment yourself.** Copy `quick.yaml` and test one hypothesis of
   your own (a 2% threshold? no history features? a new feature in dbt?). Use the AI as a
   reviewer: ask "what's wrong with this?", not "write this".
4. **Write the README results section yourself**, from the leaderboards. Your words,
   your claims, your caveats.
