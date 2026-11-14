# Experiments

Every test run on the model, in the order it was run: the question, the setup, the result, what it means, and where to reproduce it. [decisions.md](decisions.md) records the choices these experiments led to; this file records the evidence, including tests that changed nothing.

Results are never deleted. When a later experiment changes how an earlier result should be read, the earlier entry gets a note pointing forward.

## Where things stand

The question: **will a new outage start in a county (≥ 5% of customers out, with no hour at 5% or more in the 24 hours before) in the 6 hours starting 2 hours from now?** Tested on 2025, a year no model or setting saw before the final run. The 24-hour rule (E25, E26) keeps one outage hovering around the line from counting twice.

| Version | What the model knows | Onset PR-AUC (2025) | vs. warnings + outlook | Status |
|---|---|---|---|---|
| Warnings + outlook alone | NWS warnings in force, latest SPC outlook | 0.039 (0.020–0.062) | 1× | What utilities have today |
| Forecast-ready, no forecasts | Weather up to the decision, warnings and outlook, neighbouring counties, outages so far | 0.064 (0.035–0.096) | 1.6× (1.4–2.2×) | [E18](#e18-the-final-forecast-ready-model-tested-on-2025), [E26](#e26-fresh-new-outages-as-the-definition) |
| **With HRRR forecasts (mean of the last 5 runs)** | As above, plus what the five HRRR runs issued 2–6 h before the decision predicted for the window | **0.094 (0.054–0.143)** | **2.4× (2.0–3.3×)** | **Main result** ([E21](#e21-a-probability-range-from-several-hrrr-runs), E26) |
| Perfect-weather ceiling | The weather during the 6 hours it predicts | 0.100 (0.058–0.149) | 2.5× (2.1–3.4×) | Not significantly better than the main result (p = 0.08) |

Ranges are 95% storm-day bootstrap ranges on 2025; ratios are paired (both models scored on the same resampled days). Every comparison with warnings + outlook is significant at p ≤ 0.001 (E23, E26).

Alerting on the riskiest 0.75% of county-hours, 15.1% of the main model's alerts are followed by a new outage, 31× the 0.49% base rate, and it catches 30% of 2025's 1,436 new outages in time.

**How to read the scores**

- **Onset PR-AUC** ranks every scored decision by predicted probability and asks how well real new outages float to the top, from 0 to 1. The reference is the base rate: about 0.005 for "≥ 5% out, starting from calm". A score of 0.068 is about 13× that. Only *new* outages are scored, because "it's still out" is easy to predict and useless for staging crews.
- **Caught** is the share of new outages that had an alert in time: an alert at some decision hour whose window contained the outage's start.
- **Alert level** is the top 1% of the same model's scores on the 2024 validation year, fixed before 2025 is scored.
- **Alert episodes** are runs of consecutive alerted hours in one county, roughly one crew call-out each.
- **Seeds:** differences under about 2% are within the noise between random seeds. Feature and setting decisions use 3–5 seeds.
- **Ranges** (from E19 on) are 95% bootstrap ranges over 2025's storm days. One year's absolute score is uncertain, because a few storm days decide most of it. Differences between models scored on the same days are much more certain.

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
- **Result (2025, 2 h ahead).** 95% ranges come from a paired bootstrap over storm days (12 UTC to 12 UTC, 1,000 resamples, `ml/uncertainty.py`). "Same alert share" means each version alerts on its own top 0.75% of 2025 hours, the forecast-ready model's share at its frozen level. That cutoff uses the scores only, never the outcomes, so the versions are compared like for like.

  | Window weather | Onset PR-AUC | Caught, same alert share | Precision, same alert share | Alert episodes, same alert share |
  |---|---|---|---|---|
  | Warnings + outlook alone (no window weather) | 0.039 (0.019–0.062) | 10% (2–23%)¹ | 15.8%¹ | 538¹ |
  | None (the E18 model) | 0.068 (0.039–0.103) | 27% (16–38%) | 12.7% (8.8–16.5%) | 3,165 |
  | Actual (ceiling) | 0.105 (0.056–0.159) | 33% (22–44%) | 16.8% (11.9–21.1%) | 3,238 |
  | HRRR 1-hour forecasts (control) | 0.102 (0.057–0.150) | 33% (22–43%) | 16.7% (11.8–21.5%) | 3,146 |
  | **HRRR forecast issued 2 h before the decision** | **0.094 (0.051–0.145)** | **33% (22–43%)** | **15.7% (11.0–20.2%)** | 4,703 |

  ¹ The rate table gives many hours the same probability, so it can't be cut at exactly 0.75%; it alerts on 0.29% of hours at both cutoffs.

  Paired differences (same resampled days):

  | Comparison | Onset PR-AUC ratio, 95% range |
  |---|---|
  | With HRRR forecasts vs. the E18 model | 1.38× (1.18–1.58) |
  | The E18 model vs. warnings + outlook | 1.73× (1.49–2.32) |
  | With HRRR forecasts vs. warnings + outlook | 2.38× (1.98–3.25) |

  At each model's frozen level (set on 2024 with actual weather), the forecast version alerts on 1.25% of hours instead of 0.75%, with 7,393 episodes, and catches 41%. That comparison is not like for like, which is why the same-alert-share columns are the ones to quote.

- **Meaning:**
  - **Real forecasts recover about 70% of the gap** between the forecast-ready model and the ceiling: 0.068 → 0.094, against 0.105. The gain is clear: the paired range (1.18–1.58×) stays well above 1.
  - **At the same number of alert hours,** forecasts catch 33% of new outages instead of 27%, and alerts are right 15.7% of the time instead of 12.7%. They do spread those hours over more episodes (4,703 against 3,165): alerts switch on and off as successive runs move a storm around, which means more crew call-outs for the same alert time.
  - The control scores close to the ceiling (0.102), so the change of data source costs little. The rest of the drop is forecast error.
  - **One year's score is uncertain; the comparisons are not.** Every single score has a wide range (0.068 could be anywhere from 0.039 to 0.103), because a few big storm days decide most of a year. But the models win and lose on the same days, so the paired ratios are much tighter. Claims should be phrased as comparisons ("1.7× the official forecasts, 95% range 1.5–2.3×"), not as absolute scores.
  - **Limits:** the model never saw a forecast in training, so it treats forecasts as if they were observations. That mostly affects calibration (E21), not ranking. A run issued 2 h earlier is a realistic delay.

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

### E21. A probability range from several HRRR runs
- **Question:** Can each prediction come with a range, not just a number? And does averaging several runs beat the newest one?
- **Setup:** At decision hour *h*, the runs issued 2, 3, 4, 5 and 6 hours before *h* all forecast the same window. The E19 model is fed each in turn, giving five probabilities per decision (a time-lagged ensemble). The range is the lowest to the highest of the five. Scored on 1,761,636 decisions in 2025 that have all five runs, with storm-day ranges (`ml/forecast_ensemble.py`, `forecast_ensemble_2025.csv`, `forecast_ensemble_bins_2025.csv`).
- **Result: older runs score lower, and their average scores higher.**

  | Forecast used | Onset PR-AUC | vs. newest run (paired) |
  |---|---|---|
  | Run issued 2 h before (newest) | 0.094 (0.054–0.145) | |
  | 3 / 4 / 5 / 6 h before | 0.091 / 0.090 / 0.089 / 0.089 | each lower, every range below 0 |
  | **Mean of the 5 runs** | **0.099 (0.056–0.154)** | **+0.002 to +0.011** |

  Same alert share (0.75% of hours):

  | Forecast used | Caught | Precision | Alert episodes |
  |---|---|---|---|
  | Newest run | 33.5% (23–43%) | 15.7% | 4,706 |
  | Mean of the 5 runs | 30.7% (20–41%) | 16.1% | 3,058 |

  Paired, the mean catches 1.7–4.1 points fewer new outages.

- **Result: the ranges are honest.**

  | Mean probability | Decisions | Mean | Outages that followed | Average range |
  |---|---|---|---|---|
  | ≤ 0.5% | 1,405,544 | 0.19% | 0.19% | 0.18–0.21% |
  | 0.5–1% | 213,353 | 0.68% | 0.66% | 0.59–0.82% |
  | 1–2% | 77,674 | 1.4% | 1.5% | 1.1–1.9% |
  | 2–5% | 41,328 | 3.1% | 3.0% | 2.0–4.8% |
  | 5–10% | 13,128 | 6.9% | 6.4% | 4.0–11.6% |
  | 10–20% | 6,617 | 13.9% | 13.0% | 8.0–22.5% |
  | over 20% | 3,992 | 32.5% | 26.5% | 22.7–43.6% |

- **Meaning:**
  - **Averaging the runs is the better ranking,** recovering about 85% of the gap to the ceiling (0.068 → 0.099, against 0.105). It also cuts the alert flicker: fewer call-outs than even the E18 model (3,058 against 3,165), each right a little more often. The cost is a slower reaction. Older runs haven't seen a storm that just formed, so the mean catches a few points fewer new outages. **Newest run** = catch more, more call-outs. **Mean** = fewer, steadier call-outs. That's a dispatch choice, not a modelling one.
  - **The probabilities are well calibrated** up to about 20%, even though the model never saw a forecast in training: outages followed about as often as predicted. Above 20% it is overconfident (32.5% predicted, 26.5% happened). That is the expected effect of training on actual weather. It matters for the dollar rule only at the top end, and calibration on 2024 forecasts would fix it.
  - **The range is a usable per-decision uncertainty.** In every bin, the share of outages that followed falls inside the average range. A dispatcher could see "7%, range 4–12%" instead of a bare 7%. The range does carry information: at low probabilities, a wide range (one run shows a storm) means more outages than a narrow one (0.26% against 0.12%). At high probabilities a wide range means fewer (11.9% against 14.2% at 10–20%). It works as a measure of how sure the forecast is.

### E22. Pipeline audit
- **Question:** Before publishing, is anything still seeing the future, or otherwise wrong in a way the scores wouldn't show?
- **Setup:** Five checks (`ml/audit.py`, full write-up in [audit.md](audit.md)):
  - every input and label recomputed from the raw tables with explicit time filters,
  - each raw signal scored at offsets from −12 h to +12 h to check the clocks,
  - the model retrained on shuffled outcomes,
  - forecast error by forecast hour,
  - what's missing in 2025.
- **Result:**
  - 100% agreement on every recomputed input and label, including all 2,226 warning flags.
  - Skill peaks at +1 to +2 h, where the window is.
  - Shuffled outcomes score 1.3–1.4× the base rate, explained by rare weather and below an outcome-free "unusual weather" score (1.9×). The real model scores 13×.
  - Forecast error grows steadily with the forecast hour.
  - Unknown hours are spread evenly across storm and calm days.
  - 99.8% of new outages had a decision that could catch them.
- **Meaning:** No look-ahead, clock or leakage problem found. The E19–E21 results stand.

### E23. Is the difference significant?
- **Question:** The 95% ranges of single scores overlap. Are the differences between models real?
- **Setup:** Two paired tests on 2025, 2 h ahead, 366 storm days (`ml/significance.py`, `significance_2025.csv`):
  - **Paired bootstrap:** 1,000 resamples of storm days, both models scored on each one. p is the share of resamples where the challenger is not better.
  - **Storm-day permutation:** 1,000 times, each day's predictions are swapped between the two models with probability ½. Scores are first converted to within-model percentile ranks, so the swap doesn't mix two probability scales.
- **Result:**

  | Challenger vs. reference | Onset PR-AUC | Better in resamples | p (bootstrap) | p (permutation) |
  |---|---|---|---|---|
  | No forecasts vs. warnings + outlook | 0.068 vs. 0.039 | 100% | < 0.001 | 0.001 |
  | With HRRR forecasts (mean of 5) vs. warnings + outlook | 0.099 vs. 0.039 | 100% | < 0.001 | 0.001 |
  | With HRRR forecasts (mean of 5) vs. no forecasts | 0.099 vs. 0.068 | 100% | < 0.001 | 0.001 |
  | Mean of 5 runs vs. newest run | 0.099 vs. 0.094 | 100% | < 0.001 | 0.002 |
  | Ceiling (actual window weather) vs. mean of 5 runs | 0.105 vs. 0.099 | 92% | 0.085 | 0.091 |

  0.001 is the smallest p 1,000 resamples or permutations can show.

- **Meaning:**
  - **Overlapping bars don't mean "not significant".** Every model's score rises and falls with the same storms, so the single-score ranges are wide. The paired differences are not: every comparison against the official forecasts, and the gain from adding forecasts, is significant at p ≤ 0.001.
  - **The gap between real forecasts and perfect weather knowledge is not significant** (p ≈ 0.09). On 2025, the averaged HRRR runs can't be told apart from knowing the window's weather in advance.

### E24. Does canopy help in Missouri, in Illinois, or both?
- **Question:** The tree finding on the pages is a correlation: canopy goes with storm damage in Missouri (r = +0.43), not in Illinois (−0.10). Does *knowing* the canopy improve the model in each state?
- **Setup:** The E18 model (2 h ahead, no HRRR forecasts) with and without the canopy features, 3 seeds, trained 2020–2023 and scored on 2024. Done two ways (`ml/canopy_by_state.py`, `canopy_by_state.csv`):
  - **Pooled:** one model for both states, scored on each state separately.
  - **By state:** a model trained and scored on one state only.
- **Result:** the change in onset PR-AUC from adding canopy:

  | Setup | Missouri | Illinois |
  |---|---|---|
  | Pooled model, scored per state | +0.4% (−2.7% to +3.3%; better with 2 of 3 seeds) | **+3.0%** (+1.0% to +6.0%; 3 of 3) |
  | Model for one state only | −1.9% (−3.6% to +0.8%; 1 of 3) | +2.9% (−3.7% to +6.7%; 2 of 3) |

- **Meaning:**
  - **The opposite of the correlation.** Canopy helps the model a little in Illinois and not in Missouri.
  - **A plausible reading:** in Missouri, heavy canopy comes with the rest of the Ozarks (rural, hilly, older lines, few customers per county), which the model already learns from housing, density and county size. Canopy then adds nothing new there. In mostly treeless Illinois, the few wooded counties (river bluffs and valleys) stand out from their neighbours in a way the other features don't capture.
  - **Small effects.** All of these are within a few percent, close to the seed noise. The supported claim is: trees are a small, real signal overall (E7, E15), and the county correlation is not evidence that they matter more in Missouri.

### E25. Are "new outages" really new?
- **Question:** A county hovering around the 5% line (6%, then 4%, then 6%) counts as a new outage each time it climbs back over. Those re-crossings are the same outage continuing, and easy to predict. Do they inflate the scores?
- **Setup:** 2025, 2 h ahead, the same predictions as E19–E23. A *fresh* new outage has no hour at 5% or more in that county in the 24 hours before; a decision is *fresh* when the county had no such hour in the 24 hours before it. All models were rescored on fresh decisions only, with paired storm-day ranges (`fresh_onsets_2025.csv`).
- **Result:**
  - **188 of the 1,624 new outages (12%) were re-crossings.**
  - Decisions with an outage in the previous 24 hours are 2.1% of all decisions, but hold 8% of the positive windows.
  - On fresh decisions only:

  | Model | Onset PR-AUC, all | Fresh only | vs. warnings + outlook, fresh only |
  |---|---|---|---|
  | No forecasts | 0.068 | 0.064 | 1.6× (1.4–2.1×) |
  | With HRRR forecasts (newest run) | 0.094 | 0.089 | 2.3× (1.9–3.0×) |
  | With HRRR forecasts (mean of 5) | 0.099 | 0.095 | 2.4× (2.0–3.3×) |
  | Ceiling | 0.105 | 0.101 | 2.6× (2.1–3.3×) |

- **Meaning:**
  - Re-crossings make the scores about 5% higher and the advantage over the official forecasts slightly larger (2.5× against 2.4×). The conclusions don't change.
  - At first the headline kept the standard definition, with this as a robustness note. E26 adopts the fresh definition everywhere instead.
  - Predicting how long an outage lasts, or when power comes back, is a different target from this model's. It is listed under open experiments.

### E26. Fresh new outages as the definition
- **Question:** E25 showed 12% of "new outages" were the same outage climbing back over the line. With those excluded everywhere (training rows, scoring, "caught in time", the dollar estimate), what changes?
- **Setup:** A decision is kept only if no hour in the 24 hours before its window reached 5% (`data.FRESH_HOURS`, in `load_hourly`, `onset_hours` and `value_hourly.outages`). Everything from E18 to E23 rerun on 2025: 1,722,803 decisions, 1,436 new outages (against 1,624).
- **Result:**

  | 2 h ahead, 2025 | Before (E18–E23) | Fresh new outages |
  |---|---|---|
  | Warnings + outlook alone | 0.039 | 0.039 |
  | No forecasts (final features) | 0.068, 1.7× | 0.064, 1.6× (1.4–2.2×) |
  | HRRR, newest run | 0.094, 2.4× | 0.088, 2.2× (1.9–3.0×) |
  | **HRRR, mean of 5 runs** | **0.099, 2.5×** | **0.094, 2.4× (2.0–3.3×)** |
  | Ceiling | 0.105, 2.7× | 0.100, 2.5× (2.1–3.4×); vs. mean of 5, p = 0.08 |
  | Alerts at 0.75%: caught / real (mean of 5) | 31% / 16.1% | 30% / 15.1% |
  | Warnings + outlook at the same share: caught / real | 10% / 15.8% (ties: 0.29% of hours) | 17% / 10.8% (0.74% of hours) |
  | Staging value, no forecasts, typical mix | −$0.5M to $30.5M | −$2.1M to $28.2M |

  By lead time, no forecasts: 0.083 / 0.071 / 0.063 / 0.058 / 0.048 at 0 / 1 / 2 / 3 / 6 h, against 0.047 / 0.039 / 0.039 / 0.037 / 0.031 for warnings + outlook.

- **Meaning:**
  - Scores drop 5–8%, as E25 predicted, and every conclusion holds. All paired comparisons with warnings + outlook stay at p ≤ 0.001, and the gap to the ceiling stays not significant.
  - **The official baseline changed character.** Fitted on fresh rows, its rate table has fewer ties, so at the same alert share it now alerts as often as the model. It is less precise (10.8% against 15.1%) and catches about half as many new outages (17% against 30%).
  - **Neighbours are now neutral two hours ahead** (0.063 with, 0.064 without), though they still help six hours ahead (0.048 against 0.045) and with catching outages in time at 2 h (25% against 22%). They were chosen on 2024 under the old definition (E15); re-checking them on 2024 under the fresh one is open.
  - For display only, the story page's storm animation uses a version of the same model trained on every county-hour, ongoing outages included (`ml/display_model.py`), so its map tracks the outage map. It is never scored or quoted.

### E27. Neighbours under the fresh definition
- **Question:** On 2025, neighbours looked neutral two hours ahead (E26). Re-checked on the validation year, as the original choice was (E15)?
- **Setup:** `hourly_ablation.py --configs 0,1 --tag fresh`, 2024, five seeds, fresh new outages (`hourly_ablation_lead2_fresh.csv`, `hourly_ablation_lead6_fresh.csv`).
- **Result:** 2 h ahead 0.0469 → 0.0476 with neighbours (+1.5%, better with 4 of 5 seeds); 6 h ahead 0.0353 → 0.0384 (+9%, 5 of 5).
- **Meaning:** Kept. The 2025 result was within year-to-year noise; on the validation year neighbours help at both leads, most further ahead.

### E28. Calibrating the headline model on 2024 forecasts
- **Question:** Above ~20% the headline model's probabilities run high (E21). Does a calibration map fitted on 2024, with 2024's HRRR forecasts, fix it, and what is the headline model worth in dollars?
- **Setup:** The headline model trained on 2020–2023 and run on 2024 with the mean of 2024's five HRRR runs (909,774 decisions, June–December: see the note in E47); an isotonic map from probability to outcome, and an alert level frozen at its top 0.75% of 2024 hours. Both applied to 2025 (`ml/calibrate_forecasts.py`, `calibration_forecasts_2025.csv`, `value_forecasts_2025.csv`).
- **Result:**

  | Predicted band | Raw: predicted → happened | Calibrated: predicted → happened |
  |---|---|---|
  | 0.5–1% | 0.7% → 0.7% | 0.7% → 0.7% |
  | 5–10% | 7.0% → 6.5% | 5.9% → 8.1% |
  | 10–20% | 13.9% → 13.1% | 11.9% → 19.6% |
  | over 20% | 31.8% → 26.0% | 35.4% → 37.2% |

  - Onset PR-AUC 0.094 raw, 0.089 calibrated (the map flattens probabilities into ties).
  - **Alert level frozen on 2024 (7.5%):** on 2025 it alerts on 0.77% of hours, 14.8% of alerts real, 29.9% of new outages caught, 3,014 alert spells. That is almost the same as the same-share figures (0.75%, 15.1%, 30%).
  - **Dollars, typical mix, four scenarios:** raw $0.7M to $24.4M; calibrated −$0.3M to $25.0M; the model without forecasts −$2.1M to $28.2M (E26).
- **Meaning:**
  - **Calibration not adopted.** It fixes the top band but undershoots the middle, because 2024's relation between forecasts and outages differs from 2025's. The raw probabilities are as good overall, and rank better.
  - **The headline alert numbers hold with a level set in advance,** so they are achievable by a utility that fixes its alert level beforehand.
  - **In dollars, the forecast version is worth about the same as the one without forecasts.** Its extra skill is mostly on medium-risk calls, which the staging rule rarely acts on. The dollar estimate is the least certain number on the pages: two of its four inputs are assumptions.

### E29–E39. Follow-up analyses of the 2-hours-ahead model

Eleven quick analyses reusing the saved 2025 predictions, the forecast archive and the warehouse (`ml/extra_analyses.py`; results in `ml/results/extra_<name>.csv`). Fresh new outages, 2 hours ahead. "Model" is the headline model (mean of the last five HRRR runs) unless marked "without forecasts". "Caught" means alerting on each version's own riskiest 0.75% of county-hours.

### E29. Which kinds of outages it catches
- **Question:** Does it miss particular kinds of storms?
- **Setup:** Each 2025 new outage is labelled by the conditions at its onset hour: winter or cold (a winter warning, or mean temperature ≤ 2 °C), warm-season convective (CAPE ≥ 250 J/kg, or a severe-thunderstorm or tornado warning), or other (wind or rain without storm energy).
- **Result:**

  | Storm type | New outages | Caught: model | Caught: warnings + outlook |
  |---|---|---|---|
  | Warm-season convective | 767 | 41% | 29% |
  | Winter / cold | 192 | **36%** | **2%** |
  | Other (wind, rain, no storm energy) | 477 | 10% | 4% |

- **Meaning:** The largest gap is in winter. Severe-thunderstorm and tornado warnings, and the SPC convective outlook, say little about ice and snow, while the model learns from temperature, freezing level and precipitation. Outages without storm energy (a third of all new outages) are hard for both, and are the clearest place to improve.

### E30. Big outages or small ones
- **Question:** Does it catch the outages that matter most?
- **Result:** caught by the model (warnings + outlook):

  | Group | New outages | Model | Official |
  |---|---|---|---|
  | 5–10% of customers out | 747 | 23% | 12% |
  | 10–25% | 539 | 37% | 22% |
  | over 25% | 150 | 39% | 25% |
  | under 1,000 customers affected | 893 | 28% | 13% |
  | 1,000–5,000 | 482 | 32% | 22% |
  | over 5,000 | 61 | **49%** | 33% |

- **Meaning:** The bigger the outage, the more often it is caught in time, and the model's lead over the official forecasts holds at every size.

### E31. Season and time of day
- **Result:** onset PR-AUC, model against warnings + outlook:

  | Group | Model | Official | Ratio |
  |---|---|---|---|
  | Spring | 0.167 | 0.072 | 2.3× |
  | Summer | 0.036 | 0.015 | 2.4× |
  | Fall | 0.021 | 0.007 | 3.0× |
  | Winter | 0.110 | 0.037 | 3.0× |
  | Night (0–6 CT) | 0.068 | 0.019 | **3.6×** |
  | Morning (6–12) | 0.075 | 0.021 | 3.5× |
  | Afternoon (12–18) | 0.120 | 0.077 | 1.6× |
  | Evening (18–24) | 0.112 | 0.053 | 2.1× |

- **Meaning:** It is better in every season and at every time of day. The edge is largest at night and in the morning, when few warnings are issued, and smallest in the afternoon, when forecasters are most active. Summer outages are the hardest to rank for both: many scattered, short-lived storms.

### E32. The five-run range as an alert trigger
- **Result:** onset PR-AUC 0.091 (lowest run), **0.094 (mean)**, 0.083 (highest run), 0.088 (newest run); mean plus half or all of the range 0.086 and 0.078. At the same alert share they catch 30–33% and are right 14–15% of the time.
- **Meaning:** The mean is the best single number. The range is useful as a statement of uncertainty (E21), not as a better trigger.

### E33. Simple rules against the model
- **Result:** onset PR-AUC on 2025 (base rate 0.005):

  | Rule | PR-AUC |
  |---|---|
  | A severe, tornado or wind warning in force | 0.006 |
  | Share of nearby counties under warning | 0.006 |
  | Worst outage within 100 km, now | 0.009 |
  | Worst outage upwind, now | 0.008 |
  | Forecast storm energy (CAPE) in the window | 0.009 |
  | **Forecast max gust in the window (newest run)** | **0.043** |
  | Warnings + outlook (rate table) | 0.039 |
  | The model | 0.094 |

- **Meaning:** On their own, warnings in force are barely better than chance at saying where a new outage will start 2–8 hours later: they come too late and cover too much. The single best rule is the forecast gust, which on its own already matches the official forecasts. The model is 2.2× the best single rule.

### E34. Other outage sizes
- **Result:** the model without forecasts against warnings + outlook, 2025: ≥ 1% of customers 0.102 vs 0.061 (1.67×); ≥ 5% 0.064 vs 0.039 (1.63×); ≥ 10% 0.047 vs 0.029 (1.64×).
- **Meaning:** The edge doesn't depend on where the line is drawn.

### E35. Weather arriving an hour late
- **Question:** The model uses each hour's weather as soon as the hour ends, but operationally the HRRR analysis arrives about an hour late (audit, "What the audit doesn't cover"). Does that matter?
- **Setup:** The model without forecasts retrained with every weather input an hour older, both the county's own and its neighbours': the 6 hours from 7 to 1 hours before the decision instead of 6 to 0. Compared with the usual inputs, same rows, 2025.
- **Result:** 0.0643 with late weather, 0.0635 on time.
- **Meaning:** No loss: the difference is within seed noise. The last hour of weather adds nothing the hours before it don't already carry, so the 2-hours-ahead results hold with realistic data delays.

### E36. Several test years
- **Question:** Is 2025 typical?
- **Setup:** The model without forecasts trained on 2020 to the year before and tested on each of 2022–2025. The forecast model (mean of five runs) tested on 2024, trained on 2020–2023, on the 2024 decisions where all five runs exist, which are June–December (see the note in E47).
- **Result:**

  | Test year | Trained on | Model | Warnings + outlook | Ratio |
  |---|---|---|---|---|
  | 2022 | 2020–2021 | 0.018 | 0.010 | 1.8× |
  | 2023 | 2020–2022 | 0.042 | 0.026 | 1.7× |
  | 2024 | 2020–2023 | 0.048 | 0.023 | 2.1× |
  | 2025 | 2020–2024 | 0.064 | 0.039 | 1.6× |
  | June–December 2024, with HRRR forecasts | 2020–2023 | 0.066 | 0.024 | **2.8×** |

- **Meaning:** The advantage over the official forecasts holds every year (1.6–2.1× without forecasts). The absolute scores vary much more, from 0.018 to 0.064, with how much training history there is and with the year's storms. That is why the pages quote comparisons, not absolute scores.

### E37. Forecasts at every lead time
- **Setup:** The forecast model (newest run, trained on actual weather) at 0–6 hours ahead, 2025.
- **Result:** 0.107 / 0.090 / 0.087 / 0.081 / 0.071 at 0 / 1 / 2 / 3 / 6 h, against 0.047 / 0.039 / 0.039 / 0.037 / 0.031 for warnings + outlook: **2.2–2.3× at every lead**. Without forecasts, the model fell to 1.5× at 6 h (E26).
- **Meaning:** Forecasts keep the advantage steady as the lead grows. Six hours ahead they lift the score from 0.048 to 0.071.

### E38. Counties never seen in training
- **Setup:** Counties split into 5 groups; each group's 2025 decisions are scored by a model trained on the other groups' 2020–2024 (without forecasts).
- **Result:** 0.060, against 0.064 when every county is in training; warnings + outlook 0.041 (1.45×).
- **Meaning:** Most of what it learns transfers to counties it has never seen. Knowing a county's own history adds a little.

### E39. What it relies on
- **Setup:** The model without forecasts on 2025; each input group's columns shuffled across rows, and the onset PR-AUC lost (from 0.064).
- **Result:** outlook 66% of the score lost; place 33%; weather so far 24%; neighbours 16%; warnings 16%; recent outages 10%.
- **Meaning:** The SPC outlook is the backbone: it says which days are storm days. The model's skill is in using place, recent weather and neighbours to say *where* on those days. The groups overlap (a shuffled group can be partly recovered from the others), so these are a ranking, not shares that add up.

### E40–E42. Training on forecasts, and county-wide summaries
- **Question:** The headline model learns from actual weather and is fed forecasts at test time. Does it do better trained on forecasts (E40), or with forecasts summarized over the county's whole area rather than one point (E41)?
- **Setup:** Fresh new outages, 2 hours ahead, trained on 2020–2024 and scored on the same 1,731,671 decisions of 2025. Forecast windows come from the HRRR archive summarized by county (`ingest/fetch_hrrr_forecast_area.py`). E40 trains on the run issued 2 hours before each decision. E41 adds the window's strongest gust anywhere in the county, the share above storm thresholds, simulated radar, storm-column ice and lightning. E42 tests the higher-scoring of those two on 2022–2025, trained on 2020 to the year before, with the newest run (`ml/forecast_training.py`, `forecast_training_2025.csv`, `forecast_training_years.csv`, `forecast_training_calibration_2025.csv`).
- **Result:**

  | Model (2025) | Newest run | vs warnings + outlook | Mean of five runs | vs warnings + outlook |
  |---|---|---|---|---|
  | **Trained on actual weather (current)** | **0.089** | **2.27×** | **0.091** | **2.34×** |
  | Trained on forecasts (E40) | 0.080 | 2.04× | 0.080 | 2.04× |
  | Trained on forecasts + county-wide summaries (E41) | 0.082 | 2.11× | 0.082 | 2.10× |

  | Test year (E42, trained on forecasts + county-wide summaries) | Trained on | Model | Warnings + outlook | Ratio |
  |---|---|---|---|---|
  | 2022 | 2020–2021 | 0.020 | 0.010 | 2.04× |
  | 2023 | 2020–2022 | 0.049 | 0.026 | 1.94× |
  | 2024 | 2020–2023 | 0.034 | 0.023 | 1.48× |
  | 2025 | 2020–2024 | 0.082 | 0.039 | 2.11× |

  - Calibration on 2025 (E41 model): predictions in the middle bands run low (5–10%: 6.9% predicted, 9.2% happened; 10–20%: 13.7%, 17.1%); above 20%, 30.3% predicted, 28.4% happened.
- **Meaning:**
  - **The current model stays.** Neither change beat it on 2025. These are single scores without storm-day ranges or a significance test, so they show no gain, not a proven loss.
  - **County-wide summaries added a little to the forecast-trained model** (0.080 to 0.082). They haven't been tried on the current model.
  - **E42 doesn't test the current model on other years.** It still beats warnings + outlook every year, but 2.11× for 2025 isn't a clean estimate, because that version was picked on its 2025 score. Its rows differ from E21's, so its current-model score (0.091) doesn't match the headline's 0.094 exactly.

### E43. Without live outage data (for a live test)
- **Question:** A live test can get forecasts, warnings and outlooks as they are issued, but not current outages: EAGLE-I is published about a year later, and the utilities' outage maps don't allow automated collection. How much does the headline model lose without them?
- **Setup:** The headline model (mean of the five HRRR runs, 2 hours ahead, fresh new outages) retrained on 2020–2024 without its four outage inputs: the county's share out now and its worst share in the past 24 hours, and the worst neighbouring and upwind county now. Both scored on the same 1,727,693 decisions of 2025; alerts on each one's riskiest 0.75% of county-hours (`ml/live_inputs.py`, `live_inputs_2025.csv`).
- **Result:**

  | Model | PR-AUC | vs warnings + outlook | Alerts real | Caught |
  |---|---|---|---|---|
  | Warnings + outlook | 0.039 | 1× | 10.8% | 17% |
  | Headline (all inputs) | 0.094 | 2.4× (2.0–3.3×) | 15.1% | 29.9% |
  | **Without live outage data** | **0.088** | **2.2× (1.8–3.0×)** | **14.4%** | **29.5%** |

  - Against the headline model on the same storm days: 0.93× (0.88–0.98×); lower in 99.7% of resamples.
- **Meaning:** Current outages add a small, real amount (about 7% of the score), but almost nothing to the alerts: they catch the same share of new outages and are right nearly as often. A live test without outage data measures essentially the headline model, so it doesn't need a live outage source; it can be graded on EAGLE-I once 2026 is published.

### E44. Place data on its own
- **Question:** Do the place variables track how often storms cause outages, county by county? And can a correlation be mapped by county?
- **Setup:** Across the 216 counties, each variable's correlation with the storm hit rate (2020–2025), per state; housing density and customers on a log scale. Canopy's correlation again after removing the census variables linearly. For a county-level map, each county correlated with its 15, 25 or 40 nearest neighbours, against the same with canopy shuffled. An exploratory check; the correlations by state are exported by `place_data` in `scripts/make_site_figures.py`.
- **Result:**

  | Correlation with storm hit rate | Missouri | Illinois |
  |---|---|---|
  | Tree canopy | +0.43 | −0.10 |
  | Homes built before 1960 | −0.09 | +0.28 |
  | Median year built | +0.10 | −0.25 |
  | Housing density (log) | +0.02 | −0.19 |
  | Customers (log) | +0.04 | −0.17 |

  - **Canopy after the census variables:** Missouri +0.48, Illinois −0.09. In Missouri, canopy is almost unrelated to housing density (0.01) and customers (0.14).
  - **Neighbour correlations:** from about −0.5 to +0.7, with shuffled canopy reaching about ±0.4 to ±0.5. The strongest values include counties with almost no trees (Douglas, IL: 2.7% canopy, +0.68).
- **Meaning:**
  - **No census variable tracks the hit rate strongly on its own,** though shuffling place data as a group costs about a third of the score (E39). The model may use place together with the weather; this check doesn't show that it does.
  - **The Ozarks reading in E24 isn't supported by this check:** housing and customers don't account for Missouri's correlation. It is a linear check, and the model can find patterns it would miss, so why canopy adds so little in Missouri remains open.
  - **Neighbour correlations aren't reliable enough to map,** so the pages show the variables and the hit rate side by side, with one correlation per state.

### E45. The headline model without place data
- **Question:** E39 shows the model relies on place data. Does place data explain part of its lead over the official forecasts?
- **Setup:** The headline model retrained on 2020–2024 without its six place inputs, and two smaller models with no weather, all scored on the same 1,727,693 decisions of 2025; alerts on each one's riskiest 0.75% of county-hours (`ml/place_inputs.py`, `place_inputs_2025.csv`).
- **Result:**

  | Model | PR-AUC | vs warnings + outlook | Alerts real | Caught | Alert spells |
  |---|---|---|---|---|---|
  | Warnings + outlook | 0.039 | 1× | 10.8% | 16.9% | 1,047 |
  | Model on warnings + outlook only | 0.043 | 1.10× (1.06–1.28×) | 11.9% | 19.3% | 1,076 |
  | Model on warnings + outlook + place | 0.051 | 1.30× (1.15–1.56×) | 11.0% | 17.9% | 1,169 |
  | Headline without place | 0.078 | 2.0× (1.6–2.7×) | 13.9% | 28.8% | 3,259 |
  | **Headline (all inputs)** | **0.094** | **2.4× (2.0–3.3×)** | **15.0%** | **29.9%** | **2,959** |

  - Without place against the headline model on the same storm days: 0.83× (0.77–0.90×); better in 0.1% of resamples.
- **Meaning:** Place data is part of the lead: without it the model still beats the official forecasts, by less, and raises more separate alerts. Most of the lead comes from the weather. This doesn't show which place input matters, or why.

### E46. Floods as a cause of new outages
- **Question:** Are floods common enough among new outages to justify flood inputs?
- **Setup:** For every fresh new outage in 2020–2025: was a Flood or Flash Flood report filed in that county within 6 hours, and was a wind, hail, tornado or winter report filed in the same period? (`ml/flood_outages.py`, `flood_outages.csv`.)
- **Result:** Of 7,990 new outages, 174 (2.2%) had a flood report and 102 (1.3%) had a flood report and no other storm report. 6,251 (78%) had no report at all.
- **Meaning:** Floods look like a small direct cause. Reports are filed by people and many outages have none, so this is a rough size, not a cause of each outage.

### E47. More place data
- **Question:** Do tree type, size, age and dead trees, soil with recent rain, rivers, flood zones, utilities or transmission lines improve the headline model?
- **Setup:** Eleven groups of county inputs (`ingest/fetch_treemap.py`, `fetch_forest_age.py`, `fetch_soil.py`, `fetch_water.py`, `fetch_flood_zones.py`, `fetch_utilities.py`, `fetch_transmission.py`). The rule, fixed before any result: a group is kept if it beats the current model in at least 4 of 5 seeds on 2024 and on held-out counties; only the kept set and the all-groups set are scored on 2025. Selection trained on 2020–2023; the test trained on 2020–2024 and scored the same 1,727,693 decisions of 2025 (`ml/place_extra.py`, `place_extra_select.csv`, `place_extra_2025.csv`).
- **Result on 2024:**

  | Group | Inputs | Gain on 2024 | Seeds better | Gain on held-out counties | Kept |
  |---|---|---|---|---|---|
  | Tree type | 6 | −0.6% | 2 of 5 | −2.4% | No |
  | Tree size | 4 | +1.6% | 2 of 5 | +1.6% | No |
  | Dead trees and ash | 3 | +1.4% | 4 of 5 | −0.1% | No |
  | Tree age | 2 | +0.5% | 3 of 5 | +1.2% | No |
  | Soil | 5 | −0.3% | 1 of 5 | +0.4% | No |
  | Recent rain | 2 | −5.2% | 0 of 5 | −3.2% | No |
  | Soil + recent rain | 9 | −2.7% | 0 of 5 | −0.8% | No |
  | Rivers and streams | 3 | −0.1% | 3 of 5 | +3.7% | No |
  | Flood zones | 1 | −0.6% | 3 of 5 | +3.5% | No |
  | Utilities | 7 | +0.9% | 3 of 5 | −1.9% | No |
  | Transmission lines | 2 | +0.3% | 3 of 5 | −2.0% | No |
  | **Every group** | **37** | **+1.2%** | **5 of 5** | **+7.9%** | **Yes** |

- **Result on 2025:**

  | Model | PR-AUC | vs warnings + outlook | Alerts real | Caught | Alert spells |
  |---|---|---|---|---|---|
  | Warnings + outlook | 0.039 | 1× | 10.8% | 16.9% | 1,047 |
  | Current model | 0.0941 | 2.40× (1.97–3.29×) | 15.0% | 29.9% | 2,959 |
  | Every group | 0.0946 | 2.42× (1.98–3.25×) | 15.2% | 30.4% | 2,868 |

  - Every group against the current model on the same storm days: 1.005× (0.96–1.04×); better in 52% of resamples. Better with all 5 seeds, and less spread between them (0.0946–0.0954 against 0.0917–0.0948).
- **Meaning:**
  - **The current model stays.** The new data adds too little to tell from noise, for 37 more inputs. The 7.9% on held-out counties is a lead, from one seed.
  - **The 2024 selection covers June–December only.** Before June 2024 the archive stores 9 forecast hours for 20 of each day's 24 runs, and the five-run mean needs 13, so January–May (47% of 2024's positive county-hours) drops out, and most of September with it. All of 2025 has them. This also limits E28 and E36.
  - **2025 is no longer untouched.** It has been scored many times by now; the clean test of any new input is 2026.
  - **Rough inputs:** utility customers are split evenly across a utility's counties; FEMA maps are blank for 28 regions and may be partial in others; stand age is blank for 37 regions; substations aren't open; soil, river and flood data are current versions, later than the years they're used on.


### E48. Counties the outage data barely covers
- **Question:** EAGLE-I misses some utilities, so in some counties almost nobody is ever recorded out. Does the headline depend on them?
- **Setup:** Coverage = the share of hours with anyone out, 2020–2024 (no 2025 data used to choose). The headline model (mean of five HRRR runs, 2025) retrained without the 10 counties under 5% and without the 32 under 8%, each with its own warnings + outlook baseline; every model scored on all 216 counties and on the 184 well covered (`ml/coverage_test.py`, first run as a script).
- **Result:**

  | Trained on | Scored on all 216 | Scored on the 184 well covered |
  |---|---|---|
  | All counties | 2.40× (1.97–3.29×) | 2.37× |
  | Without the 10 under 5% | 2.31× | 2.34× |
  | Without the 32 under 8% | 2.31× | 2.32× |

- **Meaning:** The headline doesn't rest on the gaps. The maps mark counties under 5% as barely tracked.

### E49. Roads and trees along them
- **Question:** County-wide canopy goes with outages in Missouri but not Illinois (E24). Is it the lines? Distribution lines mostly follow roads, and no public map of them exists.
- **Setup:** Census TIGER 2023 public roads (primary, secondary, local; `ingest/fetch_roads.py`), drawn onto the canopy tiles: road km per customer, and the share of road under ≥ 50% canopy. Against each county's new outages over what a weather-only model expects (cross-fitted over 5 county folds, 2020–2025), adjusted for county size and housing density (`ml/place_fragility.py`). 206 tracked counties, cross-validated R² for log(observed ÷ expected).
- **Result:**

  | Facts | R² |
  |---|---|
  | Size (customers, housing density) | 0.577 |
  | Road per customer alone | 0.607 |
  | Size + road per customer | 0.660 |
  | … + share of road under trees | 0.709 |
  | … + co-op share | 0.706 |

  - Once size and roads are known, co-op share's partial correlation falls from +0.24 to +0.04, and county-wide canopy's from +0.20 to −0.09.
  - Transmission per home (HIFLD) added nothing.
- **Meaning:**
  - Roads and trees along them explain about a third of what size leaves unexplained. Co-ops and county-wide canopy were standing in for long, treed lines.
  - **Illinois:** the median share of road under dense canopy is 9% (Missouri 14%); 7 Illinois counties pass 25%, against 30 in Missouri. In Missouri the link appears above 25% (1.28× at 25–40%, 1.83× above 40%); between 2% and 25% neither state shows one. Consistent with a threshold Illinois rarely reaches, but too few treed Illinois counties to tell. The five-state data will test it.

### E50. Three more states (early)
- **Question:** Does the model work in states it never trained on, and does more training data help?
- **Setup:** Iowa, Indiana and Michigan added (490 counties). All weather for all five states from NOAA's HRRR GRIB archive (`ingest/fetch_hrrr_grib.py`, `ingest/grib_to_study.py`). The headline recipe trained on MO + IL only and on all five, scored on 2025 (`ml/midwest_test.py`). One training each.
- **Result:**

  | Scored on | Trained on MO + IL | Trained on all five |
  |---|---|---|
  | MO + IL | 2.57× (2.15–3.46×) | 2.80× (2.35–3.83×) |
  | IA + IN + MI, never seen by the MO + IL model | 2.96× (2.15–4.27×); caught 31% vs 19% | 4.27× (3.14–6.01×) |
  | All five | 2.76× (2.24–3.70×) | 3.54× (2.90–4.75×) |

- **Meaning:**
  - The model travels to states it never saw.
  - On MO + IL, GRIB weather gives 2.57× against the published 2.40× on Open-Meteo + hrrrzarr, so the national archive is at least as good.
  - Early: one training, ranges by storm day only; the coverage check and place data for the new states are still to run (`pixi run pipeline`).

### E51. A typical home's chance (early, Michigan only)
- **Question:** Can the forecast give a household a probability rather than a county alarm?
- **Setup:** Target: the share of a county's customers who newly lose power in the 6 hours starting 2 hours later, which is the chance for a typical home. A lower bound, since EAGLE-I counts customers per hour. Every decision hour kept; the headline features and five-run window weather; cross-entropy on the share. Against the county's usual share for the month, and against warnings + outlook (`ml/home_chance.py --states MI`).
- **Result (Michigan, 2025, 709,834 decisions):** cross-entropy skill against the usual month: model 19% (12–24%), warnings + outlook 5% (0–9%). Calibrated: when the model said 5.1%, 5.3% of homes lost power; 15.7% → 17.7%; its top bin (151 hours) says 41%, 34% happened. Warnings + outlook's top bin says 41%, 11% happened.
- **Meaning:** A household number is feasible and honest at the county level. Next: all five states, then how long the outage lasts.

### E52. Five states, every experiment (not yet reviewed)
- **Question:** Do the published results hold on Illinois, Indiana, Iowa, Michigan and Missouri (490 counties)?
- **Setup:** Every step of `pixi run pipeline` on the five-state warehouse, 2025 test year, finished 2026-11-07. Results in `ml/results/` on the `five-state` branch; `ml/results/summary.md` sets each number beside the published MO + IL one. Archived copy: `data/_archive_five_states_2026-11-07/`.
- **Result:**

  | | Five states | Published MO + IL |
  |---|---|---|
  | Model vs warnings + outlook (PR-AUC) | 3.54× (2.92–4.61×) | 2.40× (1.97–3.29×) |
  | No forecasts / perfect weather | 2.11× / 3.79× | 1.63× / 2.54× |
  | Caught at equal alerts | 35% vs 19% | 30% vs 17% |
  | Counties never trained on | 1.75× | 1.45× |
  | Without thinly covered counties (under 5% / 8%) | 3.40× / 3.31× | – |
  | Home chance, skill vs the usual month | 14% (11–17%); warnings + outlook 5.5% (3–8%) | – |

  Home chance is calibrated across the range: predicted 1.6% → 1.7% happened, 5.1% → 5.0%, 15% → 14%, 41% → 38% (170 hours). Canopy in the model (PR-AUC change from adding it, 2024): Michigan +6.2%, Indiana +3.4%, Iowa +2.4%, Illinois −3.9%, Missouri −4.1%.
- **Meaning:** Everything published holds and gets stronger with more states, but most of the jump comes from the new states (Michigan 4.99×, Iowa 3.49×). On MO + IL counties the five-state model scores 2.80×, of which the switch to GRIB weather alone accounts for 2.40× → 2.57× (E50); compare 2.80× (not 3.54×) with the published 2.40×. EAGLE-I covers the new states more thinly (23 barely tracked counties, against 10). To check before publishing: canopy now hurts in Missouri and Illinois, where the Trees slide says trees matter; E49 (roads and trees along them) should be rerun on five states.

### E53. Seven states: Minnesota and Wisconsin (headline steps only, not yet reviewed)
- **Question:** Does the gain from more states continue, and how far can this machine (32 GB) go?
- **Setup:** Minnesota and Wisconsin added to `dbt/seeds/study_states.csv` (649 counties); counties, warnings, canopy, HRRR and roads fetched; warehouse rebuilt (12 GB). Only `forecast_test`, `forecast_ensemble`, `significance` and `states` were run, overnight 2026-11-07. Results: `ml/results/seven_states_2026-11-08/` (with the run logs).
- **Result:**

  | Scored on | Trained on MO + IL | Trained on all seven |
  |---|---|---|
  | All seven | 2.87× | 3.91× (3.11–5.00×); caught 35% vs 19% |
  | MO + IL | 2.58× | 2.92× |
  | IN + IA + MI + MN + WI | 3.09× | 4.71× |
  | Wisconsin / Minnesota | 3.74× / 2.70× | 5.44× / 4.49× |

- **Meaning:** More states keep helping, most of all in the states added. Swap peaked at 16 GB: seven states is about the limit for the full code on this machine. The rest of the pipeline (other years, coverage, place, home chance) has not run on seven states.

### E54. Lean training: same answer, less training data
- **Question:** Can the headline be trained on a sample to fit more states in memory?
- **Setup:** `ml/lean_headline.py` (a draft, not part of the pipeline): every decision followed by a new outage plus 10% of the others, weighted ×10; float32; one training year in memory at a time. Compared with the full run on the same rows.
- **Result:**

  | | Lean | Full | Rank correlation | Time | Peak memory |
  |---|---|---|---|---|---|
  | Five states | 3.53× | 3.54× | 0.9956 | 8 min | 21 GB |
  | Seven states | 3.88× | 3.91× | 0.9956 | 11 min | 22 GB |

- **Meaning:** Sampling the negatives costs nothing in accuracy. It doesn't yet save memory: the training table shrinks to 0.65 GB, but loading each year with its neighbour features (12–17 GB) and building the 2025 windows for five run ages (21 GB) still dominate. For the whole country (about 5× seven states) the sampling has to move into the SQL query, the neighbour cache has to be built a few months at a time, and 2025 scored a state at a time.

### E55. The best USA model: settings and inputs re-asked on 48 states (plan, fixed before any result)
- **Question:** Most setting and input decisions (E6, E15, E16, E47) were made on Missouri + Illinois, about 1/15 of the USA's new outages. With the whole country, which of them change, and what is the best model?
- **Why these tests:** each is either a rejection that may flip with 15× the data, or new evidence that hasn't been tested as a model input:
  - Model size (E16, overfit on MO + IL); duration / spread of wind (+6% on MO + IL, `ml/wind_inputs.py`); roads + street canopy (E49: 1.8× the outages where most road is under trees, never a model input); history (E6 dropped it; the USA 6-hour benchmark ranks it first); location (the West scores lowest); the E47 place groups together (+7.9% on held-out counties, one seed); a monotone gust (warnings beat the model at gusts ≥ 35 m/s).
  - Left for later: county-wide wind, radar and lightning, and training on forecasts (E40, E41), which need the USA area archive for 2020–2023; time since the last outage, 72-hour rain and 2018–2019 (rejected on MO + IL, low prior).
- **Setup:** `ml/usa_ablation.py`. Trained on 2020–2023 (actual weather, sampled as E54), scored on every 2024 decision with the newest HRRR run's window weather (it needs forecast hours 4–9, which every 2024 run has, so all of 2024 counts). Three seeds per arm; held-out counties from 5 folds (seed 0). 2025 is not scored.
  0. **Baselines: is it more than weather with thresholds?** The current model against the strongest such rules on the same decisions: each county's own new-outage rate at each forecast gust level (< 10, 10–15, … ≥ 35 m/s), shrunk toward the national rate at that level by 200 decisions so thinly sampled counties aren't noise; the same with one national table; XGBoost on the weather inputs alone (no place, history, outages, warnings or outlook); and warnings + outlook. Reported as each baseline's score against the model's, with storm-day ranges; not a keep/drop decision.
  1. **Size**, on the current inputs: depth 6, depth 8, depth 6 with minimum child weight 100, depth 6 with 1,600 trees, depth 8 with minimum child weight 100 and 1,600 trees, each against the current settings.
  2. **Inputs**, with step 1's settings: each group added on its own against the reference.
  3. **Combine:** every kept group together against the reference, and, since more inputs may need a bigger model, the combined model with depth + 2 and with twice the trees.
- **The rule:** a change is kept if its gain on 2024 (mean of the three seeds' chances) has a 95% storm-day range above zero and at least 2 of 3 seeds are better. Held-out counties are reported, not a gate. Step 1 keeps the highest-scoring setting that passes, else the current one.
- **After E55:** the final model is scored once on 2025 with the five-run mean against the current headline and warnings + outlook (significance as E23). The clean test is the 2026 blind live test.
- **Result** (2024, PR-AUC; ranges are 95% storm-day ranges; results in `ml/results/usa_ablation_2024.csv` and `usa_ablation_verdicts.csv`):

  | Step | Arm | PR-AUC | Gain (range) | Held-out counties | Kept |
  |---|---|---|---|---|---|
  | 0. Baselines | Current model | 0.0946 | | | |
  | | Gust bins per county | 0.0539 | model 1.75× (1.57–1.94×) | | |
  | | Weather only (XGBoost) | 0.0668 | model 1.42× | | |
  | | Gust bins, national | 0.0211 | model 4.5× | | |
  | | Warnings + outlook | 0.0183 | model 5.2× | | |
  | 1. Size | Depth 6 / depth 8 | 0.1022 / 0.1064 | +8.0% / +12.5% | | yes |
  | | Depth 6, min child 100 / 1,600 trees | 0.1031 / 0.1059 | +9.0% / +12.0% | | yes |
  | | **Depth 8, min child 100, 1,600 trees** | **0.1089** | **+15.1% (11.6–19.7%)** | | **chosen** |
  | 2. Inputs | E47 place groups | 0.1124 | +3.2% (1.7–5.3%) | +8.1% | yes |
  | | Location | 0.1115 | +2.5% (1.5–3.8%) | +6.5% | yes |
  | | History | 0.1114 | +2.3% (1.3–3.4%) | +16.4% | yes |
  | | Duration / spread | 0.1112 | +2.1% (0.9–3.9%) | +2.6% | yes |
  | | Roads + street canopy | 0.1102 | +1.3% (0.7–2.0%) | +4.4% | yes |
  | | Monotone gust | 0.1084 | −0.4% (−1.0 to +0.4%) | −0.4% | no |
  | 3. Combine | **All kept groups** | **0.1154** | **+6.0% (4.0–8.7%)** | **+21.0%** | **yes** |
  | | … depth 10 | 0.1145 | −0.8% (−1.2 to −0.4%) | −0.7% | no |
  | | … 3,200 trees | 0.1144 | −0.9% (−1.2 to −0.5%) | −0.8% | no |

  Every kept arm was better on all 3 seeds; every rejected arm on none.

  **2025, scored once** (`ml/usa_final_test.py`, `ml/results/usa_final_2025.csv`; 25.3 M decisions, 150 K of them followed by a new outage (25,362 new outages, each seen by up to 6 decision hours), five-run mean):

  | Model | PR-AUC (range) | vs warnings + outlook | Precision / recall at 0.75% alerted | Best F1 |
  |---|---|---|---|---|
  | Warnings + outlook | 0.0216 (0.017–0.026) | 1× | 7.2% / 9.1% | 0.085 |
  | Current headline | 0.0868 (0.072–0.102) | 4.01× | 15.1% / 19.1% | 0.170 |
  | **E55 model (seed 0)** | **0.1021 (0.085–0.120)** | **4.72× (4.20–5.31×)** | **16.6% / 20.9%** | **0.186** |
  | E55 model, 3 seeds averaged | 0.1033 | 4.78× | 16.6% / 21.0% | 0.187 |

  The E55 model scores 1.18× the current headline (1.14–1.22×) and is better in every resample.

  **Live version** (`ml/train_live_usa.py`, `ml/results/live_usa_2025.csv`): the E55 recipe without the 4 inputs a live job can't get (the share out now and over the past 24 hours, and in neighbouring and upwind counties; 106 inputs), trained on 2020–2024 and scored on 2025 the same way. The shipping model (2020–2025) is in `live/model_usa/`.

  | Model | PR-AUC (range) | vs warnings + outlook | Live model vs this | Precision / recall at 0.75% |
  |---|---|---|---|---|
  | E55 model (with outage data) | 0.1021 | 4.72× | 0.96× (0.94–0.97×) | 16.6% / 20.9% |
  | **Live USA model** | **0.0975 (0.081–0.114)** | **4.51× (4.02–5.06×)** | | **16.2% / 20.4%** |
  | Current headline (with outage data) | 0.0868 | 4.01× | 1.12× (1.08–1.17×) | 15.1% / 19.1% |

  Alert level (top 0.75% of 2025 chances): 0.101.

- **Meaning:**
  - **It is not weather with thresholds.** The best rule built on forecast gust alone (each county's own outage rate at each gust level) reaches 57% of the model's score; XGBoost on the weather alone, 71%. The rest comes from place, history and recent outages.
  - **The whole country flips most of the Missouri + Illinois rejections.** A bigger model (rejected in E16) is the largest single gain, +15%. History (dropped in E6) and the E47 place groups now pass, and so do location, roads + street canopy and duration / spread. With 15× the outages, the model can use what was noise on two states.
  - **The new inputs help most where the model has seen least.** On held-out counties the combined gain is +21% against +6% overall, and history alone gives +16%. They describe a county the model hasn't trained on. That matters for a national map.
  - **The size settled.** With every kept input added, a deeper model or twice the trees is slightly but consistently worse. Depth 8, minimum child weight 100 and 1,600 trees is the USA setting.
  - **The monotone gust doesn't help.** Forcing chances to rise with gust does not recover the warnings' edge at gusts ≥ 35 m/s, so that gap needs another fix (training on forecasts or radar, E40–E42).
  - **The gains hold on 2025.** Every choice was made on 2024. On the untouched 2025 the new model beats the current headline by 18% and warnings + outlook by 4.7×. One caveat: duration / spread was first picked on Missouri + Illinois 2025 (`ml/wind_inputs.py`), so 2025 is not fully clean for that one input. The clean test is the 2026 blind live test.
  - **The live model loses little without outage data.** It keeps 96% of the score (4.51× vs 4.72× warnings + outlook) and still beats the current headline that uses outage data. On Missouri + Illinois the loss was about 8% (2.2× vs 2.4×, E43). With the whole country, place and history carry more of what recent outages used to tell the model.

---

## Open experiments

| Test | Why | Notes |
|---|---|---|
| The forecast model on 2022 and 2023 | The five-run recipe has only been tested on June–December 2024 and 2025 (E36); E42 covers other years with a different version | Newest run only: the five-run mean can't be computed before June 2024 (see E47) |
| More place data on unseen counties | All the new groups together gained 7.9% on held-out counties in E47, from one seed on part of 2024 | A lead only; try it on the 2026 blind test rather than on 2025 again |
| County-wide summaries on the current model | E41 only tried them on the forecast-trained model | Should be done before the blind test, since it would change the model |
| The live model at longer leads | 2 hours may be too short to move crews; E37 tested the forecast model at 0–6 hours, not the live recipe | For example 4 hours |
| Held-out storms | Split by storm instead of by year | |
| Per-storm scores | Which 2025 storms were caught, which were missed and why | By storm type in E29: wind and rain without storm energy are the hard cases |
| Roads and trees on five states | E52: canopy now lowers the score in Missouri; E49 found the link along roads in MO + IL only | Rerun E49 before rewriting the Trees slide |
| The whole country | E53–E54: seven states is the memory limit for the full code | Weather is on disk for all 3,108 counties; needs the SQL-side sampling and chunked neighbours from E54, and about 50 GB of disk for the warehouse |
| Restoration time | Next, after E51. Predict how long an outage will last once it starts (a utility's estimated time of restoration); E25 shows outages often hover around the threshold while crews work | A different target and label: hours until the county is back under 1% |
| **E57a. A neural network on the same inputs** (after the 2025 test) | E1 compared tree libraries, never a neural network; trees usually win on tables, but a network makes different mistakes, so averaging the two may gain | PyTorch on the GPU. E55's 110 inputs, rank-transformed to a normal shape (CAPE and rain are heavy-tailed), missing values as 0 plus a flag; month, hour, SPC category, state and county as learned embeddings (county: 16 numbers; dropped for 10% of training rows so it works for unseen counties). MLP 512-256-128, SiLU, LayerNorm, dropout 0.2; weighted cross-entropy with the sampling weights (no focal loss, to keep chances calibrated); AdamW, batch 8,192, cosine schedule, epochs chosen on 2024. Arms: the network alone, and the network averaged with XGBoost, each against E55's model, by E55's rule |
| **E57b. A graph network over neighbouring counties** (exploratory) | The neighbour and upwind inputs are hand-made; a graph network could learn how storms and outages spread between counties | Each hour is a graph: 3,108 counties, edges to counties within 100 km with distance, bearing and the wind's angle to that bearing. Node inputs = E57a's without the hand-made neighbour inputs. 2–3 rounds of attention message passing (GATv2 with edge features), then a per-county chance; only onset-eligible counties count in the loss. Training hours: every hour with an outage somewhere plus 10% of quiet hours, weighted. Compared with E57a's MLP without neighbour inputs (does learned spreading beat none?) and with them (does it beat hand-made?). Needs PyTorch Geometric in the gpu environment and ~25 GB of hourly tensors on disk |
| **E56. Public reports as a live outage signal** (after E55) | A live forecast has no current outage data, worth about 7% of the score (E43), and a "Now" view needs it. People's reports are also the only route below county level | First: how often each source's reports match EAGLE-I's 2025 outages (county, hour), how early they come, and which counties they miss (cities vs rural). Then, only for a source that carries signal, as a live input. Reports are self-selected: a signal and a check, never the label |
| ↳ NWS Local Storm Reports | Public domain, already read from IEM for floods (E46): "power lines down", "trees on lines", with place and time | Cheapest; start here |
| ↳ mPING (NOAA NSSL / University of Oklahoma) | Crowdsourced weather reports, wind damage included | Research API; needs a key the user requests |
| ↳ ODIN (Oak Ridge National Laboratory) | Utilities' live outage feeds, shared on purpose: the proper live source | Needs registration by the user; coverage is the utilities that joined |
| ↳ Google Trends, "power outage" | Searches by metro area spike within minutes of an outage; aggregate and anonymous | Metro areas, not counties; access at scale is limited |
| ↳ City 311 open data | Power and streetlight complaints in some cities (e.g. New York) | Patchy coverage |
| ↳ Bluesky (and Mastodon) public posts | Open firehose by design: "power's out in …" posts | Store only county-hour counts, never posts or names; place names are ambiguous. Not Reddit, Facebook, Nextdoor or X: their terms forbid it or the API is prohibitively paid |
| ↳ The site's own "out / back" buttons | Opt-in, we choose what's stored, and "back" gives outage length | Needs the site's backend (a decision pending) |
