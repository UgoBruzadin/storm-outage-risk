# Experiments

Every test run on the model, in the order it was run: the question, the setup, the result, what it means, and where to reproduce it. [decisions.md](decisions.md) records the choices these experiments led to; this file records the evidence, including tests that changed nothing.

Results are never deleted. When a later experiment changes how an earlier result should be read, the earlier entry gets a note pointing forward.

## Where things stand

The question: **will a county's power outage start (≥ 5% of customers out, from below 5%) in the next 6 hours?** Tested on 2025, a year no model or setting saw before the final run.

| Version | What the model knows | Onset PR-AUC (2025) | vs. warnings + outlook | Status |
|---|---|---|---|---|
| Perfect-weather ceiling | The weather during the 6 hours it predicts | 0.106 | 2.4× (0.044) | Best case: nobody knows that weather in advance |
| **Forecast-ready, 2 h ahead** | Weather up to the decision, warnings and outlook in force, neighbouring counties, outages so far | **0.068** | **1.7×** (0.039) | **Main result** |
| Forecast-ready, 2 h ahead, with HRRR forecasts | As above, plus what the HRRR run issued 2 h before the decision predicted for the window | 0.094 | 2.4× (0.039) | First run, one seed: [E19](#e19-hrrr-forecasts-as-issued) |

At 2 hours ahead, the forecast-ready model alerts on 0.74% of calm county-hours. 12.8% of its alerts are followed by a new outage, about 24× the 0.52% base rate. It caught 27% of 2025's 1,624 new outages in time.

**How to read the scores**

- **Onset PR-AUC** ranks every scored decision by predicted probability and asks how well real new outages float to the top, from 0 to 1. The reference is the base rate: about 0.005 for "≥ 5% out, starting from calm". A score of 0.068 is about 13× that. Only *new* outages are scored, because "it's still out" is easy to predict and useless for staging crews.
- **Caught** is the share of new outages that had an alert in time: an alert at some decision hour whose window contained the outage's start.
- **Alert level** is the top 1% of the same model's scores on the 2024 validation year, fixed before 2025 is scored.
- **Alert episodes** are runs of consecutive alerted hours in one county, roughly one crew call-out each.
- **Seeds:** differences under about 2% are within the noise between random seeds. Feature and setting decisions use 3–5 seeds.

## Data and setup

The first experiments fixed the data before any modelling. They are covered in [data-notes.md](data-notes.md) and [decisions.md](decisions.md). In short:

- **Outages:** EAGLE-I county snapshots every 15 minutes, 2018–2025, with St. Louis City and County merged into one region (216 regions in Missouri and Illinois). Hours where the national feed was down are unknown, not zero.
- **Weather:** HRRR at one point per region, from Open-Meteo's archive, which stitches the first hours of each run. This is close to observed weather, not a forecast.
- **Official forecasts:** NWS warnings (issued before the hour and in force), and the latest SPC Day 1 outlook issued before the hour.
- **Splits:** never random. The time split trains on 2020–2024 and tests on 2025. Settings are chosen on 2024 (trained 2020–2023). The county split holds out whole counties.

---

## Phase 1: 6-hour blocks

The first framing: one row per region per 6-hour block (00/06/12/18 UTC), labelled with the worst hour of outages in that block. The weather features summarize the block itself (max gust, total rain, and so on).

### E1. Baselines and model families
- **Question:** Does a model beat "the same as usual" at all, and which family?
- **Setup:** Trained on 2024, tested on 2025, and on held-out counties. Thresholds of ≥ 1%, 5% and 10%. Logistic regression, XGBoost and LightGBM against the base rate (prior) and climatology. Results in `leaderboard_quick.md`.
- **Result (≥ 5%, next year):** XGBoost 0.087, LightGBM 0.085, logistic 0.066, climatology 0.008, base rate 0.005. Tree models were ahead at every threshold, and XGBoost and LightGBM were within noise of each other.
- **Meaning:** The weather carries real signal. The choice of tree library doesn't matter, so XGBoost was kept for simplicity.

### E2. Train on all blocks or only calm ones
- **Question:** Since only new outages are scored, should the model train only on blocks that started calm?
- **Setup:** Both ways, for both libraries (`leaderboard_onsets.md`).
- **Result:** Training on all blocks was as good or slightly better on onsets (≥ 1%: 0.141 against 0.137).
- **Meaning:** Kept training on all blocks; the extra "still out" rows don't hurt. The moving-window model (Phase 2) later trains on onset rows only, since there each row is already a calm hour.

### E3. More training years
- **Question:** Does training on 2020–2024 instead of 2024 alone help?
- **Setup:** The same settings, tested on 2025 (`leaderboard_years_2024.md`, `leaderboard_years_2020.md`).
- **Result:** 0.086 → 0.101 (weather + place + recent).
- **Meaning:** Adopted. More storms beat recency. This also made a separate validation year (2024) affordable.

### E4. Settings grid
- **Question:** Which XGBoost settings, chosen on 2024 rather than on the test year?
- **Setup:** A grid over depth, min child weight, trees and learning rate on the 2024 validation year, then repeated over 5 seeds (`leaderboard_tune.md`, `leaderboard_seeds_tune.md`).
- **Result:** 800 trees, learning rate 0.03, depth 4, min child weight 20. Larger leaves helped across the grid.
- **Meaning:** These settings are used everywhere since, including the hourly model (re-checked in E16).

### E5. Run-to-run noise
- **Question:** Why did two identical runs differ by about 1%?
- **Setup:** Traced to DuckDB returning rows in varying order, and XGBoost's row subsampling depends on the order.
- **Result:** Fixed the row order; identical runs now match. The remaining seed-to-seed noise is about ±0.0007 onset PR-AUC.
- **Meaning:** Effects of 1–2% can't be judged from a single run. Every decision since uses 3–5 seeds.

### E6. History features
- **Question:** Does a county's outage history (how often and how badly it lost power in the 3 years before) help?
- **Setup:** "As of" each year, so no future years leak in (`leaderboard_final_2025.md`).
- **Result:** No gain on the 2024 validation year (0.080 against 0.081).
- **Meaning:** Left out. The place features (canopy, housing age, density) and recent outages already carry it.

### E7. Tree canopy and antecedent rain
- **Question:** Does tree cover matter? Does wet soil from earlier rain matter?
- **Setup:** Canopy removed, and rain over the previous days added, over 5 seeds on 2024 and on held-out counties (`leaderboard_ablations.md`, `leaderboard_seeds_ablate.md`, `leaderboard_wet_soil.md`).
- **Result:** Removing canopy lowered the score with every seed in 3 of 4 settings (−2.3% to −2.8%). Rain helped on held-out counties at ≥ 5% but hurt next year at ≥ 10%.
- **Meaning:** Canopy kept; antecedent rain left out as mixed. Confirmed again in E15.

### E8. Three ways to split
- **Question:** How much do random splits flatter the score?
- **Setup:** The final settings on next year, held-out counties and random region-days (`leaderboard_splits.md`).
- **Result:** Next year 0.106, held-out counties 0.086, random region-days 0.093.
- **Meaning:** Here the random split didn't inflate the score much, because blocks are long and storms vary year to year. Next-year results are reported as the main number since they're the realistic use.

### E9. A related project's setup on our data
- **Question:** How does the feature set and model of weathernext-outage-forecasting (a separate, competing project) compare on the same data?
- **Setup:** Their features, model settings and class weighting, on all three splits (`leaderboard_weathernext.md`).
- **Result (next year):** 0.053 for their XGBoost against 0.106 for ours.
- **Meaning:** The gain comes from the features (place, recent outages) and settings, not the library.

### E10. The official forecasts as a baseline
- **Question:** Does the model beat what forecasters already publish?
- **Setup:** NWS warnings and SPC outlooks turned into probabilities (a rate table fitted on training years), alone and as model features (`leaderboard_official.md`).
- **Result (≥ 5%, next year):** Warnings + outlook 0.044; the model 0.106; the model with warnings and outlook added 0.122.
- **Meaning:** The model looked about 2.4× better than the official forecasts. E12 showed most of that gap came from seeing the block's own weather.

### E11. What staging crews on the forecasts would be worth (6-hour blocks)
- **Question:** In dollars, what's the forecast worth to a utility, compared with the official forecasts?
- **Setup:** Berkeley Lab ICE outage costs for a typical customer mix. Crews shorten outages by 10% or 25%, and staging costs $5k or $20k per crew-block; both are scenarios with no published source. Every forecast stages by the same rule (probability × expected avoidable loss ≥ staging cost) (`ml/value.py`, `value_2025.csv`).
- **Result:** The model saved $3.5M–$38.8M across the scenarios. The official forecasts ranged from −$14.9M to −$0.6M. Relative economic value: model 0.52, official 0.34.
- **Meaning:** Superseded by E18. These are best-case numbers, because the model saw the block's weather.

### E12. Lead time: weather from before the block only
- **Question:** How much skill is left when the model only knows the weather up to the moment it decides?
- **Setup:** The same scored blocks and labels, with weather features shifted to the 6 hours before the decision, at 0, 1, 2, 3 and 6 hours before the block (`ml/lead_time.py`, `lead_time_2025.csv`).
- **Result:**

  | Weather known | Onset PR-AUC |
  |---|---|
  | During the block (reported model) | 0.106 |
  | Up to the block's start | 0.043 |
  | Up to the block's start, with warnings + outlook | 0.084 |
  | 1 / 2 / 3 / 6 h before the block | 0.027 / 0.025 / 0.023 / 0.020 |
  | Warnings + outlook alone | 0.044 |

- **Meaning:** This is the most important result in the project. **Most of the 0.106 came from knowing the weather during the block it predicted.** That isn't a data leak, but it answers "given perfect weather knowledge" rather than "given what you'd know in time". From here on, 0.106 is the ceiling, and the forecast-ready model is the main result.

---

## Phase 2: the moving window (forecast-ready)

The second framing, built to answer the question a utility actually faces. A decision is made every hour about the 6 hours starting *L* hours later. Every input is known at the decision hour: weather of the 6 hours before it, outages up to the hour before, warnings and the outlook in force, place, and neighbouring counties. Only the outcome window is shifted ahead. Table: `mart_study__region_1h`; benchmark: `ml/moving_window.py`.

### E13. Region-years the tracker missed
- **Question:** Some utilities weren't in EAGLE-I for whole years, which looks like "no outages". How many, and do they matter?
- **Setup:** A region-year is tracked when its share of hours with anyone out is at least a fifth of its 75th-percentile year (`mart_study__region_coverage`). The median was tried first and let McDonald County's bad years through.
- **Result:** Flags 47 region-years in 2018, 6 in 2019, and Webster and McDonald counties (MO) in 2020–2022; none after.
- **Meaning:** These rows are dropped from the hourly model. 2018–2019 are usable apart from them (see E17).

### E14. Data artifacts in the hourly table
- **Question:** Do the hourly features hold impossible values that the 6-hour summaries hid?
- **Result:** About 1,000 archive hours with over 100 mm of rain in one hour, up to 340 mm, mostly with light winds: an artifact. In the official baseline, many hours shared exactly the same probability, so "the top 1%" could flag many more by ties.
- **Meaning:** Rain over 100 mm/h is treated as unknown in the hourly table. Alerts need a probability strictly above the alert level.

### E15. Which features, hourly (2 h ahead, 2024 validation, 5 seeds)
- **Question:** Do neighbouring counties, time since the last outage, rain over the past 72 hours and canopy help the forecast-ready model?
- **Setup:** Each change against the base (weather, place, recent outages, warnings, outlook) (`ml/hourly_ablation.py`, `hourly_ablation_lead2_features.csv`, `hourly_ablation_lead6.csv`). "Neighbours" means the strongest gust, CAPE and rain, worst outage and warning share within 100 km and upwind (within 200 km, 200–290°).
- **Result:**

  | Change | Onset PR-AUC (mean of 5 seeds) | Effect |
  |---|---|---|
  | Base | 0.0544 | |
  | + neighbours | 0.0551 | +1.3% (+2.8% over 3 seeds; +5.7% at 6 h ahead) |
  | + neighbours + time since last outage | 0.0542 | mixed across seeds |
  | + neighbours + rain in the past 72 h | 0.0524 | −5% against neighbours alone, every seed |
  | + neighbours − canopy | 0.0536 | −2.7% against keeping canopy |

- **Meaning:** Neighbours kept: their gain grows with lead time, as expected when storms move in from upwind. Canopy kept. Time since the last outage (as a continuous number of hours, up to 30 days) and 72-hour rain were left out.

### E16. Settings, hourly
- **Question:** Do the 6-hour settings still fit the hourly model?
- **Setup:** Depth {4, 6} × min child weight {20, 100} × trees {800, 1500} on 2024 (`ml/hourly_tune.py`, `hourly_tune_lead2.csv`).
- **Result:** The current settings (depth 4, min child weight 20, 800 trees) scored best at 0.0548. The deepest and largest model scored 0.0425 (−22%).
- **Meaning:** Unchanged. Bigger models overfit this rare an event.

### E17. Adding 2018–2019
- **Question:** Do two more years of storms help, now that the untracked region-years are flagged?
- **Setup:** Training from 2018 against 2020, the rest unchanged (`hourly_ablation_lead2_from2018.csv`).
- **Result:** +0.5%, mixed across seeds.
- **Meaning:** Not adopted. Training stays 2020–2024.

### E18. The final forecast-ready model, tested on 2025
- **Question:** How good is the chosen model on the untouched test year, at each lead time?
- **Setup:** Trained on 2020–2024; features and settings from E15–E17; alert level fixed on 2024 (`moving_window_2025.csv`).
- **Result:**

  | Hours ahead | 0 | 1 | 2 | 3 | 6 |
  |---|---|---|---|---|---|
  | Warnings + outlook alone | 0.047 | 0.040 | 0.039 | 0.036 | 0.031 |
  | Model: weather + place + recent | 0.058 | 0.044 | 0.037 | 0.033 | 0.023 |
  | + warnings + outlook | 0.091 | 0.075 | 0.067 | 0.062 | 0.049 |
  | **+ neighbours (final)** | **0.090** | **0.077** | **0.068** | **0.065** | **0.050** |
  | Caught in time (final) | 38% | 32% | 27% | 25% | 23% |

  At 2 h ahead: alerts on 0.74% of hours, 12.8% precise, 3,154 alert episodes, against the official forecasts' 538 episodes catching 10%.

- **Meaning:** Weather alone fades quickly with lead time; the official forecasts fade slowly because they are forecasts. Combining them beats both at every lead, by 1.6–1.9×. The model's own weather features add the most at short leads, and the warnings carry it further out.

### E19. HRRR forecasts as issued
- **Question:** The forecast-ready model only knows weather that has already happened. How much does adding what HRRR *predicted* for the window add, and how much of the gap to the 0.106 ceiling is reachable in practice?
- **Setup:** Each hourly HRRR run's forecasts for the following 13 hours, from the University of Utah's hrrrzarr archive, at the same 216 points (`ingest/fetch_hrrr_forecast.py`). The first version is cheap: 2025 only. A model trained on perfect window weather is scored three ways on 2025: with the actual window weather, with the archive's 1-hour forecasts (a control for the change of data source), and with the forecast from the run issued 2 hours before the decision. Training on forecasts would need the training years too.
  The model is the E18 final model plus 15 window-weather features: the same summaries (max gust, total rain, …) over the 6 hours it predicts. It is trained on 2020–2024 with the weather that actually happened. The alert level is fixed on 2024 the same way. The forecast for a decision at hour *h* comes from the run issued at *h* − 2, which is complete by *h*. Its forecast hours 4–9 cover the window. The download is ~30 MB of map tiles per run, 2024-12-31 to 2025-12-31, 829 MB kept. 16 of 8,784 runs are missing from the archive, so 1,759,405 of the 1,768,412 decisions are scored, the same rows for every version (`ml/forecast_test.py`, `forecast_test_2025.csv`).
- **Result (2025, 2 h ahead):**

  | Window weather | Onset PR-AUC | Alerts (share of hours) | Alert precision | Caught | Alert episodes |
  |---|---|---|---|---|---|
  | None (the E18 model) | 0.068 | 0.75% | 12.8% | 27% | 3,151 |
  | Actual (ceiling) | 0.105 | 1.03% | 14.3% | 37% | 4,255 |
  | HRRR 1-hour forecasts (control) | 0.102 | 1.23% | 13.2% | 41% | 4,780 |
  | **HRRR forecast issued 2 h before the decision** | **0.094** | 1.25% | 11.9% | 41% | 7,393 |

- **Meaning:**
  - **Real forecasts recover about 70% of the gap** between the forecast-ready model and the ceiling: 0.068 → 0.094, against 0.105. That is 2.4× warnings + outlook alone (0.039).
  - The control scores close to the ceiling (0.102), so the change of data source costs little. The rest of the drop is forecast error.
  - **The alert counts are not like-for-like.** The alert level was set with actual weather, and forecasts push more hours above it: 1.25% of hours instead of 0.75%, and more than twice the episodes. "Caught" rises partly because the model alerts more. Onset PR-AUC doesn't depend on the level, so it is the fair comparison. A fair alert comparison needs the level set on 2024 forecasts, which means downloading 2024.
  - **Limits:** one seed. The model never saw a forecast in training, so it trusts forecasts as if they were observations; training on forecasts should do at least as well. A run issued 2 h earlier is a realistic delay, but a utility using the newest run would do slightly better.

### E20. What staging crews would be worth, forecast-ready (2 h ahead)
- **Question:** E11 again, with the forecast-ready model and crews staged on alert episodes.
- **Setup:** A crew is staged from 2 hours after an episode's first alert to the end of its last window. Staging is charged per 6 hours, rounded up. Any new outage inside a staged span counts as ready (`ml/value_hourly.py`, `value_hourly_2025.csv`). Typical customer mix.
- **Result:**

  | Crews shorten outages by / staging cost | Perfect foresight | Model | Warnings + outlook |
  |---|---|---|---|
  | 10% / $5k | $42.9M | $5.0M | −$3.2M |
  | 10% / $20k | $18.6M | −$0.5M | −$6.9M |
  | 25% / $5k | $124.0M | $30.5M | −$17.9M |
  | 25% / $20k | $99.7M | $8.7M | −$19.2M |

- **Meaning:** From roughly break-even to $30M in 2025, depending on the assumptions. It's a small loss only when crews help little and staging is expensive. Staging on the official forecasts by the same rule loses money in every scenario. For residential customers alone, staging never pays, because their outage costs are too small per customer. These are estimates: the crew effect and staging cost are assumptions, so the range matters more than any single figure.

---

## Open experiments

| Test | Why | Notes |
|---|---|---|
| HRRR forecasts, seeds and a 2024 alert level | E19 is one seed, and its alert level was set without forecasts | 2024 forecasts: another ~6 hours of download, ~0.8 GB kept |
| HRRR forecasts, trained on forecasts | E19 trains on actual weather and scores on forecasts | Needs 2020–2024 forecasts: ~1.5 TB of reads, ~4 GB kept |
| One hour of data delay | HRRR analyses arrive about an hour late; the model uses the last hour as soon as it ends | Drop the last hour of weather and rescore |
| Storm-day bootstrap intervals | Give every 2025 score a confidence interval; storms, not hours, are the independent units | |
| Held-out storms | Split by storm instead of by year | |
| Calibration | Are the probabilities right, not just the ranking? Needed for the dollar rule | |
| Per-storm scores | Which 2025 storms were caught, which were missed and why | |
