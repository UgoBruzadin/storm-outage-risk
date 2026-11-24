# The USA site: plan (draft for review)

Branch `site-usa` (worktree `../storm-outage-risk-site`), from `usa` at 16e2243. Nothing here is published. Every
public wording change is shown to the user before it ships.

## Scope

- The published site (`main`) covers Missouri + Illinois. This draft covers the whole lower 48 + DC: 3,108 county
  regions, 3,089 with outage records, 47 states + DC with 2025 results (Connecticut has none yet: EAGLE-I reports
  its old counties, the warehouse has its 9 new planning regions).
- Headline: E55's model (depth 8, minimum child weight 100, 1,600 trees, 110 inputs), chosen on 2024, scored once on
  2025. The clean test is still the 2026 blind live test.
- The live forecast stays the frozen Missouri + Illinois blind test (`live-v1.1`). No USA live feed exists. The page
  says so.

## Where the numbers come from

All story-page numbers are `{placeholders}` filled from `site/data/story.json`, which
`scripts/make_site_figures.py` builds (by default into `data/site_preview/`). Two kinds of sources:

| Kind | Files | Refresh |
|---|---|---|
| Pipeline outputs | `data/app/meta_hourly.json`, `ladder.parquet`, `lead_time.parquet`, `calibration.parquet`, `county_hourly.parquet`; `ml/results/moving_window_2025.csv`, `significance_2025.csv`, `extra_*.csv`, `midwest_2025.csv`, `coverage_2025.csv`, `canopy_by_state.csv`, `place_fragility.csv`, `value_hourly_2025.csv`, `value_forecasts_2025.csv`, `benchmark_final_2025.csv`; `data/cache/display_2025.parquet` | **Old recipe today (Nov 12).** The running pipeline overwrites them with E55's recipe. Rebuild story.json after it finishes. |
| E55 one-off scripts | `ml/results/usa_ablation_verdicts.csv` (`ml/usa_ablation.py`), `usa_final_2025.csv` (`ml/usa_final_test.py`), `live_usa_2025.csv` (`ml/train_live_usa.py`) | Final. Not in the pipeline, so not overwritten. |

New in story.json (`usa_data()` in make_site_figures.py): `e55`, `live_usa`, `baselines`, `choices`, `states_results`,
`coverage`, `scope`, `build_up`.

## Story page (site/index.html + site/text.yaml)

Section order changes: the USA storm opens the page; the MO + IL live map moves near the end, labelled as the
blind test. ✱ = new section.

| # | Section (id) | What it shows | Numbers / data (story.json ← file, column) | vs MO + IL page |
|---|---|---|---|---|
| 1 | Storm (`storm`) | May 16–17 2025 (prototype's storm 5), hour by hour, one USA map: risk decided 2 h before (fill) and counties ≥ 5% out in the window (outline, toggle). Zoom buttons + drag. | `storm[]` ← `data/cache/display_2025.parquet` (p_mean, p_low, p_high) and `marts.mart_study__region_1h` (pct_out); `scope.counties` | Was March 14–15, MO + IL, two side-by-side maps. Still the display version (counts outages already underway), said so |
| 2 | Data (`data`) | Five sources → one table | `pipeline.hours` ← count of `mart_study__region_1h` 2020–2025; `pipeline.tests` ← `dbt ls`; `scope.counties` | Weather now from the NOAA HRRR GRIB archive (E50); place adds roads, soil, flood zones |
| 3 | Traps (`traps`) | Same three traps | `heartbeat` (warehouse); `persistence` ← `benchmark_final_2025.csv` (pr_auc, onset_pr_auc, 6-hour version); `ladder` values for the timeline | Trap 3 text now uses the USA hourly ladder (ceiling / no forecasts / with forecasts) instead of MO + IL's 0.106 → 0.043, which moves to the write-up |
| 4 | Result (`ladder`) | Ratio to warnings + outlook, 5 rungs, with storm-day ranges | `ladder[]` ← `data/app/ladder.parquet`; `e55.vs_previous*` ← `usa_final_2025.csv` (`ratio_vs_current headline*`); `alerts.base_rate` ← meta `event_rate` | Note adds: the E55 model vs the previous headline, and random ≈ base rate |
| 5 ✱ | Not thresholds (`baselines`) | Share of the model's 2024 score reached by: warnings + outlook, national gust table, each county's own gust table, weather-only XGBoost | `baselines[]` ← `usa_ablation_verdicts.csv` stage `baselines` (`pr_auc`, `reference_pr_auc`) | New (E55 step 0) |
| 6 ✱ | Re-asked on the whole country (`choices`) | E55's choices on 2024: gain with 95% range, kept or not, gain on held-out counties | `choices[]` ← `usa_ablation_verdicts.csv` (`gain`, `gain_lo`, `gain_hi`, `kept`, `held_out_gain`); 2025 check ← `e55` (`usa_final_2025.csv` row `new model`) | New (E55 steps 1–3 + the one-time 2025 test) |
| 7 | Lead time (`lead`) | Score by hours ahead, observed weather only | `lead_time[]` ← `moving_window_2025.csv` (FINAL_RUN = E55 rung); `build_up[]` (lead 2, every rung) | Final line is now the E55 rung |
| 8 | Alerts (`alerts`) | Same alert budget: outages caught, alerts real | `alerts.*` ← meta `at_headline_share` (caught = share of the 25,362 new outages with an alert in time) | MO + IL's "fixed level set on 2024: 14.8% / 29.9%" removed: no USA source yet |
| 9 | Trust (`ranges`) | Calibration bins | `calibration[]` ← `calibration.parquet` | Same |
| 10 ✱ | State by state (`states`) | Ratio with 95% range per state, sorted; states under 50 new outages flagged and not ranked | `states_results[]` ← `midwest_2025.csv`, rows `trained_on` = `all N` (ratio, ratio_lo, ratio_hi, new_outages, model_caught, official_caught) | New |
| 11 | Where (`where`) | USA county map: share of new outages caught; hatched = under 3 new outages | `accuracy` ← `county_hourly.parquet`; `coverage.thin` ← `place_fragility.csv` (`tracked` = False) | USA map; the lead names the 419 barely covered counties |
| 12 | Holds up (`holds`) | Tabs: years, storm types, unseen counties, ✱ thin coverage | `holds` ← `extra_years.csv`, `extra_storm_types.csv`, `extra_counties.csv`; ✱ `coverage` ← `coverage_2025.csv` | New tab: trained without barely covered counties |
| 13 | Trees (`trees`) | Place maps (USA) + storm hit rate / outages beyond the weather | `canopy`, `place`, `lines` (as now); `choices` row "roads + street canopy"; `canopy.model` ← `canopy_by_state.csv` | Text rewritten: MO-vs-IL claims gone. Correlations over all counties. The R² claim (size 58% → 71%) is TODO for the USA |
| 14 | Value (`value`) | Net savings, 4 scenarios | `value` ← `value_hourly_2025.csv`, `value_forecasts_2025.csv` | USA totals are in the hundreds of millions to billions: see open decision 6 |
| 15 | Blind test (`live`) | The frozen MO + IL live map (unchanged feed), clearly labelled; one line on the USA live model | `live_usa` ← `live_usa_2025.csv` (`live USA model (held out)` row; `live_vs_this` of the E55 row) | Moved from first to near the end; renamed "The blind test"; says the USA feed isn't built |
| 16 ✱ | The app (`app`) | Plan for the public county map: Now…+6 h, find your county, Low / Elevated / High, out / back reports, a list for utilities. No forecast numbers (nothing live to show) | `live_usa.alert_level`; level cut-offs = TODO (decision 2) | New |
| 17 | End (`end`) | Next steps, links | – | Next steps updated |

Small-sample rule on the page: a state with fewer than `states_min` (50) new outages in 2025 is listed as "too few to
judge", with no ratio. Today that hides DC (1), Delaware (3) and Rhode Island (17). Massachusetts (53), New Hampshire
(58) and New Jersey (59, range 1.7–29×) pass but have very wide ranges: their whiskers are drawn clipped.

## Write-up (site/writeup/writeup.md)

Chapters (✱ new or rewritten for the USA):

1. Hero, stats, summary ✱ (USA scope, E55 headline, live caveat)
2. How it started (MO + IL origin kept, then "from two states to the country" ✱)
3. The question, asked honestly (inputs table updated to the 110 inputs ✱)
4. Results: two hours ahead ✱ (USA ladder, E55's one-time 2025 test, alert table; precision / recall per decision-hour vs outages caught, defined)
5. ✱ Choosing the model on the whole country (E55: baselines, size, inputs, combine; the rule; 2025 once)
6. How sure is it? (ranges, significance, calibration, the audit, updated for the new inputs ✱)
7. ✱ State by state (table, small-sample flags, why PR-AUC is compared as a ratio)
8. What it learned / does it hold up (years, storms, unseen counties, coverage ✱)
9. Trees (MO + IL finding kept as history; USA results TODO ✱)
10. How it compares (unchanged; MO + IL era, labelled)
11. What it would be worth (USA scale ✱; open decision 6)
12. Pitfalls with code (unchanged, plus ✱ 15: "a new outage counted six times" (150 K decision-hours vs 25,362 outages), ✱ 16: "the outage tracker grew" (history drift))
13. How it's built, limitations ✱ (coverage, Connecticut, history drift, 2025 used once, extreme gusts)
14. ✱ The app (plan)

Write-up numbers are typed into the Markdown (the write-up has no placeholders). Every number marked `TODO(rerun)`
must be refreshed from the file named next to it after the pipeline finishes.

## The app section

What the page promises: a plan, not a product. Draws on the prototype (`~/jobs/outage-site/`, canvas artifact):

- **Phone home:** search an address, see the county's chance a new outage starts, tabs Now, +1 h … +6 h, a level
  badge (Low / Elevated / High), "Why" (top drivers), next 24 h.
- **Desktop map:** USA county map, zoom / pan, hover, click for the county panel, storm replay.
- **Reports:** "My power is out" / "It's back", and comments. Opt-in. A signal and a check (E56), never the label.
- **For utilities:** counties to watch, alert flag at the tested level, five-run range, CSV.
- **What's needed first:** a USA live feed (new model tag; the MO + IL blind test stays frozen); live models at 0
  and 1 h ahead for "Now" and "+1 h" (only 2 h exists; "Now" also lacks current outages, E43 / E56); a backend for
  shared reports; Connecticut's county crosswalk.

## Open decisions for the user

1. **Site name.** "Storm Outage Risk" (current) vs "Will my power go out?" (prototype's headline) vs other. Repo and
   URL stay `storm-outage-risk` either way?
2. **Low / Elevated / High cut-offs.** Options: (a) relative to the tested alert level (High = top 0.75% of
   county-hours, today p ≥ `live_usa.alert_level`; Elevated = top 5%?); (b) fixed chances (prototype: High ≥ 4%,
   Elevated ≥ 1% on the home chance; the map used 0.5 / 2 / 5 / 8.4%); (c) multiples of the county's usual chance.
   Whichever, the levels need their own 2025 check (precision / caught per level) before going public.
3. **Backend for shared reports:** Supabase (Postgres, row-level security, free tier) vs Firebase (Firestore,
   anonymous auth) vs Cloudflare (Workers + D1, Turnstile against bots). All three can store county-hour counts only.
4. **Anonymity and moderation.** Store reports as county + hour counts only? Free-text comments at all? If yes:
   moderation (pre-moderated, word filter, report button), rate limits, retention period.
5. **The old 6-hour model.** Traps 2 and 3 and the write-up's comparison with weathernext-outage-forecasting use the
   first, 6-hour version. Keep them as history (draft does), or cut them.
6. **The value slide at USA scale.** Today's (old recipe) USA estimate: the model without forecasts nets $133 M to
   $1.23 B, warnings + outlook −$301 M to +$505 M. Keep, shrink to the write-up, or drop? The assumptions
   (restoration 10 / 25%, $5k / $20k staging per county) were sized for MO + IL utilities.
7. **Small-sample cut-off** for states: 50 new outages (draft), or also require a 95% range narrower than some width.
8. **Page weight.** USA story.json is about 3–4 MB (county shapes + 31 storm hours × 3,108 counties). Accept,
   simplify shapes more, or load the storm frames lazily.
9. **Which storm opens the page.** Draft: May 16–17 2025 (as the prototype). Alternative: the biggest 2025 storm by
   new outages (`data/app/storms.parquet`).
10. **Live section placement.** Draft moves it near the end. Keep it first while the blind test runs?

## TODO: numbers not produced yet (or produced by the old recipe)

| Number | Where used | Produced by | Status |
|---|---|---|---|
| Already rewritten by the rerun (Nov 14): `moving_window_2025.csv` (five rungs; final 0.064 at 2 h vs 0.058 with neighbours), `forecast_test_2025.csv` (newest run 0.0955, ceiling 0.1145, no forecasts 0.0643, warnings 0.0216) | sections 3, 4, 7; write-up Results | pipeline | Typed into the write-up; page reads them via story.json once rebuilt |
| Headline ladder (all rungs), alerts, calibration, lead time, years, storm types, unseen counties, per state, coverage, canopy by state, value | page sections 4, 7–14; write-up | the running pipeline (`forecast_test`, `forecast_ensemble`, `significance`, `extra`, `states`, `coverage`, `canopy_by_state`, `place_fragility`, `value_hourly`, `export_hourly`) | Old recipe now; refreshes on rerun |
| Storm May 16–17 risk frames | section 1 | `ml/display_model.py` → `display_2025.parquet` (must cover the whole country and those hours) | Rerun; then `make_site_figures.py --story` |
| R² of size / roads / road-under-trees on outages beyond the weather (USA) | trees note, write-up | `ml/place_fragility.py` prints it but saves no file: add a small CSV (e.g. `place_fragility_r2.csv`) | TODO |
| Alert level fixed on 2024, applied to 2025 (USA) | was in the alerts note | `ml/forecast_test.py` (MO + IL had 14.8% / 29.9%) | TODO, not produced for the USA |
| Precision / caught per Low / Elevated / High level | app section | a new small script on `forecast_ensemble_2025.parquet` once cut-offs are chosen | TODO |
| Extreme-gust weakness (warnings beat the model at ≥ 35 m/s) | write-up limitations | E55 text says so; the 0.74× figure is from `notebooks/explore_usa.ipynb`, not a results file | Quote without the number until a results file has it |
| Model vs warnings by time of day / storm type for the USA (6×, 3.6×…) | write-up | notebook only | Not quoted |
| Typical-home chance skill (USA) | app section, write-up | `ml/home_chance.py` → `home_chance_2025.csv` | Rerun |

## Unsure

- After the rerun, is the five-run headline in `meta_hourly.json` exactly E55's model (seed 0)? Expected, since
  `forecast_test` now uses E55's recipe, but check that its PR-AUC matches `usa_final_2025.csv` (0.102).
- "3,053 counties" in `midwest_2025.csv` (counties with 2025 decisions) vs 3,089 with outage records vs 3,108 regions.
  The page uses 3,108 (map) and 3,089 (with outage data); the write-up explains the 3,053.
- Per-state "caught" uses each state's own riskiest 0.75% of county-hours, not the national alert level.
- E55's "recall 20.9%" is per decision-hour (`usa_final_2025.csv`, 150,122 positive decision-hours); the page's
  "outages caught" is per new outage (meta `at_headline_share`). Different numbers for related questions; both are
  defined where they appear.
