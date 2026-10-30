# Pipeline audit

Checks that the moving-window results ([experiments.md](experiments.md), E13–E21) mean what they say: every input is known at the decision, the sources agree on the clock, the model can't find the answer some other way, and the test year isn't quietly thinned. Run before anything is published, and again after any change to the pipeline:

```bash
pixi run python -m ml.audit                    # all checks, ~40 min (two retrains)
pixi run python -m ml.audit --checks timing    # one check
```

Results are written to `ml/results/audit_<check>.csv`. Last run: October 2026, 2025 test year, 2 hours ahead. **All checks passed.**

## 1. Every input is known at the decision (`timing`)

For 20,000 random 2025 decisions, each input and the label was recomputed from the raw tables with an explicit time filter, then compared with what the model was given.

| Recomputed from the raw tables | Decisions | Match |
|---|---|---|
| Max gust, the 6 hours before the decision (HRRR) | 20,000 | 100% |
| Total rain, the 6 hours before the decision | 20,000 | 100% |
| Share out in the hour before the decision (EAGLE-I) | 20,000 | 100% |
| Worst hour of the 24 hours before | 20,000 | 100% |
| Worst outage within 100 km, the hour before | 20,000 | 100% |
| SPC category, from the latest outlook issued before the decision | 20,000 | 100% |
| Label: the worst hour of *h* + 2 … *h* + 7 | 20,000 | 100% |
| The hour before the window (*h* + 1), used only to select new outages | 20,000 | 100% |
| **Every** 2025 severe/tornado warning flag: a warning issued before *h* and still in force | 2,226 | 100% |
| HRRR forecast: max gust from the run issued at *h* − 2, valid *h* + 2 … *h* + 7 | 2,000 | 100% |

The first version of the warning check reported 11 flags without a warning. All 11 were the merged St. Louis City + County region, whose ID the check didn't split. Each had a warning issued before the hour.

## 2. The sources agree on the clock (`shift`)

One raw signal at a time was scored against the 2-hour-ahead label, with the signal moved from 12 hours before to 12 hours after the decision. If the sources' clocks agree, skill peaks where the signal overlaps the window, at an offset of +2. A source in local time instead of UTC would move the peak by 5–6 hours.

| Signal | Peak offset | PR-AUC at peak | At −12 h / +12 h |
|---|---|---|---|
| Max gust over 6 hours (HRRR) | +1 h (+2 h: 0.0435) | 0.0440 | 0.008 / 0.010 |
| Severe or tornado warning in force (NWS) | **+2 h** | 0.0357 | 0.005 / 0.005 |

HRRR, NWS and EAGLE-I agree to within an hour. The gust peak sits one hour early, as expected: outages start early in the window, and the wind that causes them comes just before.

## 3. The model can't find the answer another way (`shuffled`)

The model was retrained on 2020–2024 with the outcomes shuffled, then scored on the real 2025 outcomes. With nothing true to learn, it should score near the base rate.

| | Onset PR-AUC | × base rate |
|---|---|---|
| Base rate (2025) | 0.0052 | 1.0× |
| Random scores (20 draws) | 0.0052 (highest 0.0054) | 1.0× |
| **Trained on shuffled outcomes** (2 seeds) | **0.0066, 0.0075** | **1.3–1.4×** |
| "How unusual is the weather" (no outcomes used) | 0.0100 | 1.9× |
| The real model, no forecasts | 0.068 | 13× |

The small excess over the base rate is not a leak. A model fitted to noise gives its most extreme scores to rare weather, where few training rows average the noise out. Rare weather is also where outages happen, as the outcome-free "unusualness" score shows. Nothing in the features, the row order or the pipeline lets the model recover the outcomes.

## 4. Forecast hours are what they claim (`forecast`)

HRRR forecast error against what happened, by forecast hour, over 2025 (1.9 million region-hours per forecast hour):

| Forecast hour | 1 | 3 | 6 | 9 | 13 |
|---|---|---|---|---|---|
| Gust error (m/s) | 0.82 | 1.12 | 1.28 | 1.35 | 1.42 |
| Gust correlation, gusty hours (≥ 15 m/s) | 0.61 | 0.55 | 0.52 | 0.50 | 0.49 |
| Temperature error (°C) | 0.37 | 0.68 | 0.90 | 1.01 | 1.09 |
| Rain error (mm/h) | 0.10 | 0.14 | 0.16 | 0.16 | 0.17 |

Error grows steadily with the forecast hour for every variable, as it should. Mis-indexed forecast hours would break that pattern. One known difference: HRRR's surface CAPE in the archive runs 60–100 J/kg below Open-Meteo's even at hour 1, which is likely a different CAPE definition. The 1-hour control in E19 shows that this source difference costs little.

## 5. The test year isn't quietly thinned (`missing`)

| 2025 region-hours | Count | Label unknown | Outage count unknown |
|---|---|---|---|
| Storm days (any region ≥ 20% out) | 705,024 | 4.5% | 5.6% |
| Other days | 1,187,136 | 4.5% | 5.5% |

Unknown hours, mostly when EAGLE-I's national feed was down, are spread evenly. They don't cluster on storm days. **1,620 of the 1,624 new outages in 2025 (99.8%)** had at least one scored decision that could have caught them. The other 4 count as missed in every "caught" figure.

## What the audit doesn't cover

- **One test year.** The checks confirm 2025 is scored correctly, not that 2025 is typical. That needs several test years (open in experiments.md).
- **Real-time delays.** The checks use archive timestamps. Operationally, the latest hour of HRRR and EAGLE-I arrives late; the forecast run's 2-hour age covers this for HRRR, not for EAGLE-I.
- **Zone-to-county warnings** are checked through the mapping table, whose correctness rests on its dbt tests.
