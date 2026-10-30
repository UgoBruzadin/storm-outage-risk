<!--
The write-up page (site/writeup/index.html) shows this file. Edit, save, refresh; no build step.
Locally, serve the site folder (python3 -m http.server -d site) and open http://localhost:8000/writeup/.

Plain Markdown, plus five conventions:
  ::: name  ...  :::            a styled box: hero, buttons, stats, abstract, pitfall, note, footer
  ## Heading {#id}              sets the heading's link anchor (the contents list links to #id)
  ![alt text](../assets/x.jpg?v=5 "Caption")   an image with a caption under it; bump ?v= after replacing the file
  > A line starting with >      a small grey note (under tables, at the end of a pitfall card)
  `Data · path/to/file.sql`     on its own line at the top of a pitfall card: the card's tag
In the buttons box, a **bold** link is the blue one. Text inside ``` fences is code; -- and # comments show grey.

The link preview (title, description) is in the <head> of site/writeup/index.html.
-->

::: hero
# ⚡ Storm Outage Risk

When a storm moves through, which counties will lose power in the next few hours? This model ranks every county, every hour, by its risk of a new outage two hours ahead, using only what a utility would know at the time, including the weather forecasts available then. That tells utilities and emergency managers where to send repair crews before the lines come down.

::: buttons
- [← The two-minute story](../)
- **[Open the live dashboard](https://storm-outage-risk.streamlit.app)**
- [Code on GitHub](https://github.com/UgoBruzadin/storm-outage-risk)

:::
::: stats
- **216** counties across Missouri and Illinois, every hour, 2020–2025
- **2.5×** better than NWS warnings and SPC outlooks alone at ranking new outages two hours ahead (95% range 2.1–3.4×)
- **31×** more likely than average: county-hours the model alerted on were followed by a major new outage 16% of the time
- **31%** of 2025's 1,624 major new outages caught in time, alerting on 0.75% of county-hours

:::
::: abstract
## Summary

**The problem.** Before severe weather, utilities send repair crews to wait near where they expect damage. Forecasts say when a storm will arrive, but not where it will cut the power. The same storm can take out 2% of one county and 40% of the next.

**What I built.** A model that, every hour, estimates for every county the chance that at least 5% of its customers lose power in the six hours starting two hours later. It uses only what is known at that moment: the weather so far, the latest HRRR weather forecasts, the warnings and outlooks in force, outages so far in the county and its neighbours, and what the place is like (tree cover, housing, density).

**How well it works.** Tested on 2025, a year it never trained on, it ranks new outages 2.5× better than official warnings and outlooks alone (95% range 2.1–3.4×). Alerting on the riskiest 0.75% of county-hours, 16% of its alerts were followed by a major new outage, 31 times the average, and they caught 31% of all of them. Every prediction comes with a range from the last five forecast runs, and the ranges are honest: outages followed about as often as predicted.

**The trap I fell into.** The first version scored better still, but it summarized the weather *during* the hours it was predicting, which nobody knows in advance. Rebuilt so that every input is known at the decision, its score fell by a third; real forecasts win most of that back. A separate audit then checked that no input sees the future.

**What it would be worth.** Staging crews wherever the model pointed in 2025 would have been worth from about break-even to \$30 million, depending on assumptions about crews. That estimate is for the model without HRRR forecasts; acting on the official forecasts the same way loses money in every scenario.

**Where the effort went.** Mostly into making the numbers trustworthy. Public data hides traps: gaps that look like "no outages", one county's outages reported under its neighbour's code, and a model that looks great by predicting outages already underway, or by seeing the storm it is supposed to forecast. Each is written up below, with the code that fixes it.

- [How it started](#story)
- [The question, asked honestly](#question)
- [Results](#results)
- [How sure is it?](#sure)
- [What it learned](#findings)
- [How it compares](#compare)
- [What it would be worth](#value)
- [Pitfalls, with code](#pitfalls)
- [How it's built](#built)
- [Limitations](#limits)

:::
:::
## How it started {#story}

This began as a SQL exercise: hourly weather from St. Louis Lambert airport joined to EAGLE-I outage counts, to see whether bad weather lined up with outages in St. Louis. It did, and it raised a better question. When a storm crosses the state, which counties go dark, and why does the same storm take out 2% of one county and 40% of the next? My guess was trees, old dense canopy over overhead lines, and old housing. Testing that guess honestly turned out to be the hard part, and so did a second question I hadn't asked at first: how far ahead can anyone know?

Partway through I found a related project, [weathernext-outage-forecasting](https://github.com/biplovbhandari/weathernext-outage-forecasting), which forecasts county outages from weather forecasts and evaluates on random days. This one differs where it matters for an honest answer: place features, splits by time and by county, scoring **new** outages separately from ongoing ones, and every input fixed at the moment of the decision.

![Two county maps of Missouri and Illinois for the evening of 14 March 2025: the risk of a new outage decided at 4 PM from the forecasts available then, highest across eastern and southern Missouri, beside the worst share of customers out between 6 PM and midnight, with the largest outages in east-central and southeastern Missouri. Counties already out are gray.](../assets/social.jpg?v=5 "The 14–15 March 2025 tornado outbreak, a storm the model never trained on. Left: the risk for 6 PM to midnight, decided at 4 PM from the forecasts available then. Right: what happened. Gray counties were already out, so there was nothing new to predict. The story page plays the whole storm hour by hour.")

## The question, asked honestly {#question}

A utility decides at some hour whether to send crews somewhere for the next few hours. So the model makes a decision every hour, for every county, about the six hours that start two hours later: the time it takes to get a crew in place. Every input must be known at that hour:

::: table-wrap
| Input | As of the decision |
|----|----|
| Weather so far (HRRR: gusts, wind aloft, shear, storm energy, rain, ice) | the 6 hours before |
| Weather forecast for the window (HRRR runs, as issued) | runs issued 2–6 hours before |
| NWS warnings, SPC Day 1 outlook | issued before, in force |
| Outages in the county and within 100 km / upwind | the hour before |
| Place: tree canopy, housing age, density, size | fixed |

:::
It wasn't built this way at first. The first version worked in fixed 6-hour blocks and summarized the weather *during* each block: the strongest gust, the total rain. That's not a bug in the code, and it scored 0.106, 2.4× the official forecasts. But it answers "given the weather that actually happened, which counties lost power?", and nobody has that weather two hours ahead. Moving the weather to before the decision showed how much of the score came from seeing the storm itself:

::: table-wrap
| 6-hour blocks, new ≥ 5% outages, 2025 | PR-AUC |
|----|----|
| Weather during the block (the first version) | 0.106 |
| Weather up to the block's start | 0.043 |
| Weather up to the block's start + warnings + outlook | 0.084 |
| Weather up to 1 / 2 / 3 / 6 hours before the block | 0.027 / 0.025 / 0.023 / 0.020 |
| Warnings + outlook alone | 0.044 |

:::
So the model was rebuilt on an hourly table of 15 million county-hours, where each decision sees only what came before it, and then given the one thing the first version had for free: what the weather would do in the window. Not the weather that happened, but the HRRR forecast as it was issued, read from the University of Utah's archive of every hourly run.

## Results: two hours ahead {#results}

Scores are **PR-AUC** on new outages: how well real outages rank ahead of false alarms. Guessing at random scores the outage rate itself, about 0.005. Trained on 2020–2024, with features and settings chosen on 2024, tested once on 2025.

![Left: horizontal bars of PR-AUC on new outages two hours ahead, with 95% ranges: warnings plus outlook alone 0.039; the model with weather observed so far 0.068, 1.7 times official; with the latest HRRR forecast 0.094, 2.4 times; with the last five HRRR forecasts 0.099, 2.5 times; and the ceiling of knowing the weather in advance 0.105, 2.7 times. Right: score against hours ahead from 0 to 6: the model with warnings and outlook falls from 0.090 to 0.050, the model with weather so far only from 0.058 to 0.023, warnings and outlook alone from 0.047 to 0.031, with the HRRR forecast version at 0.099 two hours ahead.](../assets/results.jpg?v=5)

::: table-wrap
| New ≥ 5% outages, 2 hours ahead, 2025 | PR-AUC (95% range) | vs. warnings + outlook (95% range) |
|----|----|----|
| NWS warnings + SPC outlook alone | 0.039 (0.020–0.063) | 1× |
| Model, weather observed so far | 0.068 (0.040–0.103) | 1.7× (1.5–2.3×) |
| Model + latest HRRR forecast | 0.094 (0.054–0.145) | 2.4× (2.0–3.2×) |
| Model + last five HRRR forecasts | **0.099 (0.056–0.154)** | **2.5× (2.1–3.4×)** |
| Ceiling: knowing the window's weather | 0.105 (0.060–0.161) | 2.7× (2.3–3.6×) |

:::
> 1,756,605 decisions (every county-hour of 2025 not already in an outage), 1,624 new outages. XGBoost, 800 trees of depth 4; the model with forecasts is the same model given 15 more features, the window's weather, and trained on the weather that actually happened.

- **Real forecasts recover about 85% of what perfect knowledge would add.** From 0.068 with only the weather so far to 0.099 with forecasts, against 0.105 with the actual weather: 1.46× (1.26–1.67×), paired on the same storm days.
- **Averaging the last five runs beats the newest run alone** (0.099 against 0.094, better on the same days). Each run places the storm a little differently; the average is steadier.
- **Every difference above is significant** (paired storm-day permutation test, p ≤ 0.002), except one: the ceiling is not significantly better than the model with real forecasts (p = 0.09). On 2025, the averaged forecasts can't be told apart from knowing the weather in advance.
- **Weather that has already happened fades within hours.** On its own it beats the official forecasts only at 0–1 hour ahead. Warnings and outlooks fade slowly, because they are forecasts. Combining them beats both at every lead, by 1.6–1.9×.
- **Neighbours help more the further ahead.** Outages and storms in counties within 100 km and upwind added 3% two hours ahead and 6% six hours ahead, with every seed: storms in Missouri mostly arrive from the west and southwest.

### If a utility acted on it

To compare alerts fairly, every version alerts on the same share of county-hours, its own riskiest 0.75%. (Fixing the alert level on 2024 instead works for the versions trained and tested on the same kind of weather, but forecasts push more hours over a level set on actual weather, which would flatter the forecast versions.)

::: table-wrap
| Alerts on 0.75% of county-hours, 2025 | Alerts that were real | New outages caught | Alert spells |
|----|----|----|----|
| Warnings + outlook alone¹ | 15.8% | 10% | 538 |
| Model, weather observed so far | 12.7% | 27% | 3,159 |
| Model + latest HRRR forecast | 15.7% | **33%** | 4,695 |
| Model + last five HRRR forecasts | **16.1%** | 31% | **3,050** |
| Ceiling | 16.8% | 33% | 3,236 |

:::
> Base rate: 0.52% of county-hours were followed by a new outage. An alert spell is a run of consecutive alerted hours in one county, roughly one crew call-out. ¹ The rate table gives many hours the same probability, so it can only be cut at 0.29% of hours.

The newest run catches a few more outages; the average of five makes a third fewer call-outs, because alerts stop switching on and off as successive runs move a storm around. Which is better is a dispatch choice, not a modelling one. The official forecasts are about as precise, but they point at far fewer places, so they miss two-thirds of what the model catches.

## How sure is it? {#sure}

### How sure is the score?

One year's score depends on a handful of big storm days. Resampling 2025's storm days (12 UTC to 12 UTC, so an evening storm isn't cut at midnight) a thousand times gives the ranges above: any single score is uncertain, 0.099 could plausibly be anywhere from 0.056 to 0.154. But every version wins and loses on the same days, so the comparisons are much tighter: with forecasts, 2.5× the official forecasts, never less than 2.1× in 95% of resamples. Claims on these pages are phrased as comparisons for that reason. Resampling hours instead of days would have given ranges several times too narrow (pitfall 13).

Overlapping ranges don't mean "not significant", so the differences were tested directly, two ways, each paired over 2025's 366 storm days: the share of 1,000 resamples in which one model beats the other, and a permutation test that swaps the two models' predictions on randomly chosen storm days 1,000 times.

::: table-wrap
| Comparison, 2 hours ahead | Better in resamples | p (permutation) |
|----|----|----|
| Model, weather so far vs. warnings + outlook | 100% | 0.001 |
| Model + last five HRRR forecasts vs. warnings + outlook | 100% | 0.001 |
| With forecasts vs. without | 100% | 0.001 |
| Last five runs vs. the newest run | 100% | 0.002 |
| Ceiling vs. last five runs | 92% | 0.09 |

:::
> 0.001 is the smallest p 1,000 permutations can show. Code: `ml/significance.py`.

### How sure is each prediction?

The runs issued 2, 3, 4, 5 and 6 hours before a decision all forecast the same window, each with its own errors. Feeding each through the model gives five probabilities: the average is the prediction, the lowest and highest are its range. Grouped by prediction, outages followed about as often as predicted, inside the range every time:

::: table-wrap
| Predicted chance | County-hours | Average range | An outage followed |
|------------------|--------------|---------------|--------------------|
| 0.2%             | 1,405,544    | 0.18–0.21%    | 0.19%              |
| 0.7%             | 213,353      | 0.6–0.8%      | 0.66%              |
| 1.4%             | 77,674       | 1.1–1.9%      | 1.5%               |
| 3.1%             | 41,328       | 2.0–4.8%      | 3.0%               |
| 6.9%             | 13,128       | 4.0–11.6%     | 6.4%               |
| 13.9%            | 6,617        | 8.0–22.5%     | 13.0%              |
| 32.5%            | 3,992        | 22.7–43.6%    | 26.5%              |

:::
Only the riskiest group runs high (32.5% predicted, 26.5% happened): the model learned from the weather that actually happened and takes the forecasts a little too literally. The range carries information too: among low-risk hours, a wide range (one run shows a storm) was followed by twice as many outages as a narrow one.

### Did anything see the future?

After the first version's mistake, the pipeline was audited before publishing ([docs/audit.md](https://github.com/UgoBruzadin/storm-outage-risk/blob/main/docs/audit.md)):

- For 20,000 random decisions, every input and the label recomputed from the raw tables with explicit time filters matched what the model was given, 100%. All 2,226 warning flags in 2025 had a warning issued before the hour and still in force.
- Scoring the raw gust and warning signals at offsets from 12 hours before to 12 hours after the decision, skill peaks exactly over the predicted window: the sources agree on the clock.
- Retrained on shuffled outcomes, the model scores 1.3–1.4× chance, against 13× for the real one; the small excess comes from rare weather, not a leak.
- Forecast error grows steadily with the forecast hour, and missing data is spread evenly between storm and calm days.

## What it learned {#findings}

- **More years of storms helped more than any feature.** Training on 2020–2024 instead of 2024 alone lifted every score by 17–28% on the same 2025 test. Adding 2018–2019 as well, once the counties EAGLE-I wasn't tracking those years were dropped, changed nothing.
- **Neighbours and forecasts help; history doesn't.** Time since a county's last outage, rain in the previous 72 hours, and each county's outage record over three years all added nothing or hurt on the validation year, over five seeds.
- **Place helps for known counties, not new ones.** County size, housing and canopy add 25–34% on the next year but almost nothing on unseen counties: the model learns which counties are fragile more than why.
- **Tree canopy is a small, real effect, just not where the map suggests.** Removing it lowers the score by about 3% overall, with every seed. Tested state by state, it improves the model in Illinois (+3.0%, 3 of 3 seeds) and barely in Missouri (+0.4%), the opposite of the county correlation below. Still an association, not a cause.
- **Tuning barely matters, and bigger is worse.** Deeper trees or more of them overfit this rare an event, by up to 22%.

### Trees matter, just not the way I expected

I expected tree-heavy counties to fail more often in storms, and in Missouri they do. But Missouri's most wooded counties are the Ozarks, also remote, hilly and sparsely served, and the model already sees that through housing, density and county size. Given the tree data, it barely improves in Missouri (+0.4%) and improves a little in Illinois (+3.0%), where the few wooded river counties stand out from the farmland around them. Code: `ml/canopy_by_state.py`.

::: grid2
![Map of Missouri and Illinois counties shaded green by average tree canopy: the Ozark counties of southern Missouri are darkest, near 70%, while central Illinois farm counties such as Champaign are near 2%.](../assets/canopy-map.jpg?v=3 "Average tree canopy per county (USFS / NLCD 2021): Ozark forest near 70%, central Illinois farmland near 2%.")

![Scatter plot of tree canopy against storm hit rate, one dot per county, colored by state: a weak overall trend (r = 0.20), rising with canopy among Missouri counties and flat among Illinois counties.](../assets/canopy-scatter.jpg?v=3 "Canopy against how often a reported storm becomes an outage, 2020–2025. A weak link overall (r = 0.20) that comes from Missouri (+0.43); in Illinois there is essentially none (−0.10). Missouri's most wooded counties are the remote, hilly Ozarks, so terrain and access for repair crews are tangled up with the trees.")

:::
### Where it works, and where it doesn't {#where}

![Two county maps for 2025, two hours ahead. Left: share of each county's new outages caught in time by the alerts, mostly between 10% and 60%. Right: actual outage windows divided by the sum of predicted probabilities, orange where the model underrated a county and blue where it overrated one; hatched counties had fewer than three new outages.](../assets/accuracy.jpg?v=5 "Per county, 2025, two hours ahead, with alerts on the riskiest 0.75% of county-hours. Left: the share of new outages caught in time. Right: actual outage windows against what the probabilities added up to; orange counties had more than predicted. Northern Illinois had too few outages to judge (hatched). The same view is on the dashboard.")

### The resilience scorecard

![Map of Missouri and Illinois counties shaded by outage hours per customer per year, 2020 to 2025; the darkest counties are in the southeastern Missouri Ozarks, with others in northwest Missouri and central Illinois.](../assets/map.jpg?v=3 "Outage hours per customer per year, 2020–2025. The median county loses about 5 hours a year; the worst lose more than 18.")

::: table-wrap
| County | State | Customers | Outage h / customer / yr | Events / yr | Storm hit rate | Tree canopy |
|----|----|----|----|----|----|----|
| Reynolds | Missouri | 4,024 | 31.5 | 85 | 49% | 71% |
| Wayne | Missouri | 7,134 | 21.0 | 68 | 13% | 67% |
| Mercer | Illinois | 8,972 | 20.4 | 33 | 19% | 11% |
| Bollinger | Missouri | 5,897 | 19.9 | 65 | 9% | 47% |
| Lawrence | Missouri | 9,841 | 19.4 | 32 | 4% | 15% |
| Putnam | Illinois | 2,501 | 18.8 | 32 | 24% | 17% |
| Shannon | Missouri | 3,195 | 18.4 | 57 | 12% | 68% |
| Iron | Missouri | 5,709 | 18.2 | 45 | 22% | 68% |

:::
> The eight counties with the most outage hours per customer, 2020–2025. An event is a run of 6-hour blocks with ≥ 1% of customers out; storm hit rate is the share of blocks with a NOAA storm report that became one. All 216 counties are on the dashboard's Resilience scorecard.

## How it compares {#compare}

### Against the official forecasts

A utility watching a storm already has NWS warnings (severe thunderstorm, tornado, high wind, winter) and SPC's Day 1 convective outlook. Turned into a baseline, they give the historical outage rate for every combination of warnings in force and outlook risk level, learned on 2020–2024 and taken exactly as they stood at each decision. That is the first row of the results above: 0.039 two hours ahead. The model with forecasts scores 2.5× that (2.1–3.4×), and uses the warnings and outlook as inputs too: on their own, the model's weather features beat them only an hour or two ahead, and together they beat both at every lead.

Counting warnings honestly matters. A first version that counted any warning touching the 6-hour block made warnings look nearly twice as good. Of 1,445 new ≥ 5% outage blocks in 2025, 335 had a severe thunderstorm or tornado warning somewhere in the block but only 65 had one in force at its start; the rest were issued as the storm, and often the outage, arrived.

### Against weathernext-outage-forecasting's setup

Compared on the first, 6-hour version of the model, where its setup fits. The related project publishes no scores, so its setup is reproduced here on this project's data, from its code: weather features only (mapped to the closest HRRR fields), a boosted tree and a logistic regression with balanced class weights, the same ≥ 5% label, and an 80/20 split by hash of county + date.

::: table-wrap
| New ≥ 5% outages, PR-AUC | Random days (their split) | Unseen counties | Next year |
|----|----|----|----|
| Their setup: boosted tree | 0.059 | 0.058 | 0.053 |
| Their setup: logistic regression | 0.031 | 0.031 | 0.046 |
| This model | **0.093** | **0.086** | **0.106** |

:::
- **1.5–2× their score on every split.** Place and recent-outage features, and shallower trees without class weights, make the difference; the gap is widest on the next year.
- **Their headline metrics hide it.** On random days their setup reports ROC-AUC 0.77 and, at a 0.5 cut-off, 60% recall, which reads well, but only 2% of those alerts are real (F1 0.04). Class weighting buys recall by flooding the alert list.
- **Not their model.** They use Google's WeatherNext forecasts at 24–48 h lead in Alabama; this reproduces the method, not their inputs or region.

### Against published research

The closest operational work is the University of Connecticut and Eversource outage prediction model, running since 2015: machine-learning ensembles over high-resolution weather forecasts, vegetation, land cover and infrastructure, predicting outage counts up to three days ahead (Cerrai et al., 2019, *IEEE Access*; Watson et al., 2020, *The Journal of Engineering*), extended to communities across the Eastern U.S. (Taylor et al., 2023, *Energy Reports*). Earlier work modeled hurricane outages with generalized additive models and random forests (Han, Guikema & Quiring, 2009, *Risk Analysis*, and later work by Nateghi and colleagues). Those studies predict outage counts for a single utility's territory, mostly for named storms, with utility data this project doesn't have, so their scores aren't comparable. What this project adds is a public-data, multi-utility, county-level version for everyday convective and winter storms, evaluated on a future year and on new outages only.

## What it would be worth {#value}

A better score only matters if it changes a decision. The decision here: two hours before a storm window, a utility can send repair crews to wait in a county. Staging costs money every time. It pays off only if that county then loses power, because restoration starts sooner and customers are out for less time. So the question is: if a utility had staged crews wherever each forecast pointed in 2025, how much would it have saved?

![Estimated net savings in 2025 from staging crews two hours ahead, four scenarios each: perfect foresight 18.6 to 124.0 million dollars, the model with weather observed so far from a loss of 0.5 million to a gain of 30.5 million, and warnings plus outlook from a loss of 19.1 million to a loss of 3.2 million.](../assets/value.jpg?v=2)

Turning outages into dollars takes four inputs. Two come from published data, two are assumptions, so the estimate is a range over four scenarios.

::: table-wrap
| Input | Value | Source |
|----|----|----|
| What an outage costs a customer, by length | home: about \$6 for 1 hour, \$14 for 8; small business: about \$630 and \$3,500; large business: about \$6,000 and \$28,000 | Berkeley Lab's Interruption Cost Estimate (ICE) models |
| Customer mix | 88% homes, 11% small and 1% large businesses | about the U.S. mix by customer count (EIA) |
| How much a staged crew shortens an outage | 10% or 25% | assumption |
| Cost of staging a crew in a county for 6 hours | \$5,000 or \$20,000 | assumption |

:::
Each outage's length and the number of customers affected come from EAGLE-I. A crew is staged for an alert spell (consecutive alerted hours in a county), from two hours after its first alert to the end of its last window, and charged for every 6 hours of that, rounded up. It is ready for any new outage that starts in that span. Every forecast stages by the same rule, set on 2020–2024 data only: stage when its probability times the county's average avoidable loss per new outage is at least the staging cost.

::: table-wrap
| Net savings in 2025 | Shortened 10%, \$5k | 10%, \$20k | 25%, \$5k | 25%, \$20k |
|----|----|----|----|----|
| Perfect foresight (the ceiling) | \$42.9M | \$18.6M | \$124.0M | \$99.7M |
| Model, weather observed so far | **\$5.0M** | **−\$0.5M** | **\$30.5M** | **\$8.7M** |
| Warnings + outlook | −\$3.2M | −\$6.9M | −\$17.9M | −\$19.1M |

:::
- **The estimate: from about break-even to \$30 million in 2025** across Missouri and Illinois. It is a small loss only when crews help little and staging is expensive. Acting on the official forecasts by the same rule loses money in every scenario: they point at too many places.
- **The rule is close to the best it could be.** Given each forecast's best cutoff in hindsight, chosen on 2025 itself, the model would save \$35.2M in the 25%, \$5k scenario against \$30.5M by its own rule, and the official forecasts \$12.5M at best.
- **Businesses carry the value.** Counting only what outages cost households, staging never pays, even with perfect foresight: a home loses about \$14 in an 8-hour outage. Almost all the avoided cost is businesses', so the estimate moves with the customer mix.
- **For the model without forecasts.** The forecast version ranks better and makes fewer call-outs, but the dollar rule uses its probabilities directly, and above 20% they run high (see How sure is it?). Its estimate waits for a calibration step fitted on 2024 forecasts.
- **What the estimate is not.** It counts customers' losses, not the utility's own costs, and it covers one year.

Code: `ml/value_hourly.py`; results in `ml/results/value_hourly_2025.csv`.

## Pitfalls, with code {#pitfalls}

Each of these produced a plausible-looking wrong answer before it was caught. The fixes live in the dbt models and Python modules named on each card, and most are guarded by a test. Cards 1–10 were found on the first, 6-hour version of the model; the fixes carry over to the hourly one.

::: pitfall
`Data · dbt/models/intermediate/int_eaglei__blocks_6h.sql`

### 1. A missing row is not a zero

EAGLE-I only writes a row for a county that has customers out. No row can mean "no outages", or it can mean the collector was down. In one county the two look identical. Across the whole country they don't: somewhere in the U.S. someone is always without power, so a block with few national snapshots means the system was down.

```
-- national "heartbeat": how many 15-min snapshots exist in each 6-hour block
SELECT {{ block_6h('snapshot_time') }} AS block_start, count(*) AS n_snapshots
FROM (SELECT DISTINCT snapshot_time FROM {{ ref('stg_eaglei__outages') }})
GROUP BY 1

-- then, per county and block (mart_study__region_6h.sql)
CASE WHEN NOT b.eaglei_ok        THEN NULL   -- system down: unknown
     WHEN o.region_fips IS NULL  THEN 0      -- system up, no row: a real zero
     ELSE o.peak_out END AS peak_out
```

> Without this, outage-free blocks and blind blocks get the same label, and the model is trained on holes in the data.

:::
::: pitfall
`Data · dbt/models/intermediate/int_study__outages_6h.sql`

### 2. Duplicate snapshots double the outage

In early September 2025 every snapshot was recorded twice. Summing counties into regions directly would double every outage in those weeks. The fix is to collapse to one value per county per 15-minute slot first, and only then add counties together.

```
WITH per_county_slot AS (
    SELECT fips_code, snapshot_time, max(customers_out) AS customers_out  -- keep one copy
    FROM {{ ref('stg_eaglei__outages') }}
    GROUP BY ALL
)
SELECT {{ region_fips('fips_code') }} AS region_fips, snapshot_time,
       sum(customers_out) AS customers_out                               -- now it's safe to add
FROM per_county_slot
GROUP BY ALL
```

:::
::: pitfall
`Data · dbt/macros/region_fips.sql`

### 3. One county filed under its neighbour's code

From mid-2020 to 2024, St. Louis County's outages were reported under St. Louis City's FIPS code. Taken at face value, the County (about 594,000 customers) had zero customers out for three straight years, while the City's worst outage grew from 5,533 in 2019 to 83,685 in 2023, nearly 80% of its 107,000 customers. Both are modeled as one region, through a macro used everywhere a county code enters the pipeline.

```
-- largest outage per year, EAGLE-I as published
year   St. Louis County (29189)   St. Louis City (29510)
2019          28,721                     5,533
2022               0                    21,020
2023               0                    83,685
2024               0                    14,527

{% macro region_fips(column) -%}
    CASE WHEN {{ column }} IN ('29189', '29510') THEN '29189+29510' ELSE {{ column }} END
{%- endmacro %}
```

:::
::: pitfall
`SQL · dbt/models/marts/mart_study__region_6h.sql`

### 4. `least(100, NULL)` is 100

The label caps percent-out at 100. In DuckDB, `least()` skips NULLs, so a blank outage count came back as "100% of customers out", a fake catastrophe in every block with a missing count.

```
-- wrong: least(100.0, 100.0 * NULL / customers) = 100
CASE WHEN g.peak_out IS NULL OR g.peak_out > 1.5 * g.customers THEN NULL
     ELSE least(100.0, 100.0 * g.peak_out / g.customers) END AS peak_pct_out
```

> A dbt test (`assert_pct_null_when_peak_null`) fails the build if it ever comes back.

:::
::: pitfall
`Geo · ingest/fetch_tree_canopy.py`

### 5. The raster's "no data" value was a real value

The tree-canopy GeoTIFF tags 0 as "no data", but 0 means "no trees". `rasterio.mask` honours the tag, so every treeless pixel was dropped and farm counties came out about 45% forest instead of about 2%. The fix reads raw pixels, draws the county shape itself, and masks the real no-data codes (254/255).

```
pixels = src.read(1)
inside = geometry_mask([geometry], out_shape=pixels.shape, transform=src.transform, invert=True)
values = pixels[inside]
values = values[values <= 100]           # 254/255 = no data; 0 stays: it means no trees
```

:::
::: pitfall
`Modeling · ml/data.py`

### 6. A model that predicts outages already underway

Outages last for hours, so the previous block's outage is a superb predictor of this one. With it, PR-AUC on all blocks jumps to 0.42. That is a real forecast, of whether an outage will continue, but it answers a different question from this project's: which calm county goes dark next. Mixing the two inflates the score fourfold and hides how well the model does on the question that matters for staging crews. Scored only on **new outages** (blocks whose previous six hours were calm), the same model scores 0.106. (That 0.106 also saw each block's own weather: card 11.)

```
df["is_onset"] = df["prev_block_pct_out"].notna() & (df["prev_block_pct_out"] < threshold_pct)
# every benchmark reports both: pr_auc (all blocks) and onset_pr_auc (new outages only)
```

::: table-wrap
| XGBoost, ≥ 5%, next year | All blocks | New outages only |
|--------------------------|------------|------------------|
| Weather only             | 0.062      | 0.068            |
| \+ place, recent outages | 0.420      | **0.106**        |

:::
:::
::: pitfall
`Evaluation · ml/splits.py`

### 7. The hardest test changed when the data did

Splitting region-days at random puts neighbouring counties hit by the same storm on both sides, which I expected to flatter the model most. It didn't. Trained on 2024 alone, the *next year* was the hard test: 0.056 for weather only, against 0.083 on unseen counties. With five training years that gap closed, and counties the model has never seen became the hardest test. Year-to-year differences were mostly a shortage of storms; a new place stays genuinely hard. Every result is reported on both.

```
if kind == "time":                               # train 2020–2024, test 2025
    assert max(train_years) < min(test_years)
elif kind == "county":                           # no county in both train and test
    GroupKFold(n_splits=folds).split(df, groups=df["region_fips"])
```

::: table-wrap
| XGBoost, ≥ 5%, new outages, PR-AUC | Random days | Unseen counties | Next year |
|------------------------------------|-------------|-----------------|-----------|
| Weather only, trained on 2024      | 0.084       | 0.083           | 0.056     |
| Weather only, trained on 2020–2024 | 0.069       | 0.070           | 0.068     |
| Final model, trained on 2020–2024  | 0.093       | 0.086           | 0.106     |

:::
:::
::: pitfall
`Evaluation · ml/metrics.py`

### 8. Ties in "top 1%" flatter the baseline

The historical-average baseline gives every block in a county-month the same score. Taking "everything at or above the 99th percentile" then flags far more than 1% of blocks, and its recall looks better than it is. Alerts are now exactly the top *k*, with ties broken at random (seeded).

```
k = max(1, int(round(top * len(p))))
order = np.lexsort((np.random.default_rng(0).random(len(p)), -p))   # by score, ties random
alert = np.zeros(len(p), dtype=bool); alert[order[:k]] = True
```

:::
::: pitfall
`Modeling · ml/benchmarks/seeds_ablate.yaml`

### 9. One run's feature importance is an anecdote

With LightGBM on one year of data, removing tree canopy cost 12–22% of next-year PR-AUC, which would have confirmed my starting guess. XGBoost shrank or reversed the effect. Later, rain in the days before a storm looked like a 2–4% gain in a single run. Both were then repeated with five random seeds: canopy's effect held (lower score without it, with every seed, in three of four settings) and rain's didn't (better in some settings, worse in others). Feature decisions are now made on the seed average, against the seed-to-seed spread.

```
features:
  - weather+place+recent
  - weather+place+recent-canopy      # canopy removed
  - weather+place+recent+wet_soil    # antecedent rain added
models:
  - name: xgboost
    params: {..., random_state: [0, 1, 2, 3, 4]}   # every run, five times
```

:::
::: pitfall
`Modeling · ml/data.py`

### 10. Same code, same data, different answer

The same model on the same rows scored 0.1053, 0.1059 and 0.1065 in three runs. DuckDB scans tables in parallel and returns rows in a different order each time; XGBoost samples 80% of rows per tree by position, so a different order meant a slightly different model. The ~1% wobble was as large as the feature effects being judged. One line fixed it, and every reported result was rerun.

```
SELECT ...
FROM m
WHERE m.has_weather AND m.peak_pct_out IS NOT NULL
ORDER BY m.region_fips, m.block_start    -- a fixed order: row subsampling depends on it
```

:::
::: pitfall
`Modeling · dbt/models/marts/mart_study__region_1h.sql`

### 11. The model saw the storm it was predicting

The first version summarized the weather *during* each 6-hour block it scored: the block's strongest gust and total rain. No row leaked into another and every test passed, but the model was answering "given this storm, who loses power?", not "who will lose power?". It scored 0.106; with weather only up to the block's start, 0.043. The hourly table makes the boundary explicit in the window frames: features look only backwards from the decision, labels only forwards from two hours after it.

```
max(gust_ms) OVER w6                AS gust_max_ms,   -- the 6 hours BEFORE the decision
max(pct_out) OVER f2                AS fut_max_pct_2  -- the label: 2 to 7 hours AFTER it
...
WINDOW w  AS (PARTITION BY region_fips ORDER BY hour),
       w6 AS (w ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING),
       f2 AS (w ROWS BETWEEN 2 FOLLOWING AND 7 FOLLOWING)
```

> The window's weather comes back only as a forecast issued before the decision. `ml/audit.py` recomputes every input from the raw tables to check that it stays that way.

:::
::: pitfall
`Evaluation · ml/forecast_test.py`

### 12. An alert level set on one kind of input flatters another

The alert level was fixed on 2024 as the top 1% of the model's scores, with the weather that actually happened as input. Fed forecasts on 2025, more hours crossed it: 1.25% instead of 0.75%, with 7,393 alert spells instead of 3,151. The forecast version "caught" 41% of new outages, against 27%, partly just by alerting more. Alerts are now compared at one shared alert share; the cutoff uses each version's own scores and never the outcomes.

```
cut = np.quantile(p, 1 - EQUAL_SHARE)        # each version's own top 0.75% of 2025 hours
flagged = p > cut                            # strictly above: ties can't widen the alert list
```

::: table-wrap
| Model + latest HRRR forecast         | Hours alerted | Caught | Alert spells |
|--------------------------------------|---------------|--------|--------------|
| Level fixed on 2024 (actual weather) | 1.25%         | 41%    | 7,393        |
| Same share as the other versions     | 0.75%         | 33%    | 4,695        |

:::
:::
::: pitfall
`Evaluation · ml/uncertainty.py`

### 13. Hours aren't independent, storm days are

The test year has 1.76 million decisions, which makes any range computed over them look tiny. But the hours of one storm rise and fall together, and a few storm days decide most of the score. Ranges come from resampling whole storm days, 12 UTC to 12 UTC as SPC counts them, and every model is scored on the same resampled days, so differences between models get their own, much tighter, ranges.

```
def storm_day(hours):
    return (pd.to_datetime(hours) - pd.Timedelta(hours=12)).dt.floor("D")   # 12 UTC to 12 UTC

counts = rng.multinomial(n_days, np.full(n_days, 1 / n_days), size=1000)  # days drawn per resample
w = counts[i][day_of_row]                                                 # each row weighs as its day
```

> A test checks the weighted score against scikit-learn's `average_precision_score` with the same weights.

:::
::: pitfall
`Data · ml/audit.py`

### 14. Three sources, three clocks?

Outages come from EAGLE-I, weather from HRRR, warnings from NWS. If one of them were in local time instead of UTC, every feature would be five or six hours off and nothing would fail. The check: score one raw signal against the label with the signal moved hour by hour. Skill must peak where the signal overlaps the predicted window.

```
for offset in range(-12, 13):
    at = df.block_start + pd.Timedelta(hours=offset + 5)     # the 6 hours from decision + offset
    v = rolling_6h_max_gust.stack().reindex(pd.MultiIndex.from_arrays([at, df.region_fips]))
    rows.append({"offset_hours": offset, "pr_auc": average_precision_score(df.y[ok], v[ok])})
```

> Gusts peak at +1 hour and warnings at +2, where the window starts: the clocks agree.

:::
## How it's built {#built}

::: pipeline
::: step
**Ingest**Python scripts download outages, HRRR weather and the HRRR forecast archive (4 map tiles per run, 216 points kept), storm reports, NWS warnings, SPC outlooks, tree canopy rasters and Census tables.

:::
::: step
**Transform**dbt on DuckDB: staging → intermediate → marts, 61 tests, a 15-million-row hourly table with backward-looking features and forward-looking labels.

:::
::: step
**Model**XGBoost and baselines; a validation year; seed repeats; storm-day bootstrap ranges; an audit for look-ahead and leakage; MLflow tracking.

:::
::: step
**Serve**Streamlit dashboard and this site on precomputed files, packaged with Docker; CI on GitHub Actions.

:::
:::
Python, SQL, DuckDB, dbt, pixi, scikit-learn, XGBoost, MLflow, geopandas, rasterio, numcodecs, Streamlit, Plotly, D3, Docker, GitHub Actions. Every experiment and its result is logged in [docs/experiments.md](https://github.com/UgoBruzadin/storm-outage-risk/blob/main/docs/experiments.md).

### Limitations {#limits}

::: note
**One test year.** 2025's ranges cover which storms happened to hit, not how different another year could be; testing on 2023 and 2024 too is the next step. **Archive timestamps.** The model uses each hour's weather and outage counts as soon as the hour ends; in practice HRRR analyses arrive about an hour late (the forecast runs already allow two hours). **Trained on actual weather.** The forecast version is scored on forecasts but learned from what happened, so its highest probabilities run high and its dollar value is not yet estimated. **One weather point per county**, and EAGLE-I coverage that is patchy before 2020.

:::
Data: U.S. DOE / Oak Ridge National Laboratory EAGLE-I power outage data ([doi:10.13139/ORNLNCCS/1975202](https://doi.org/10.13139/ORNLNCCS/1975202)); NOAA HRRR via [Open-Meteo](https://open-meteo.com) and the University of Utah HRRR archive on AWS; NOAA NCEI Storm Events; NWS warnings and SPC outlooks via the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu); USFS / NLCD Tree Canopy Cover; U.S. Census Bureau ACS and TIGER boundaries. Map tiles © OpenStreetMap contributors, © CARTO.

Ugo Bruzadin Nunes · [github.com/UgoBruzadin/storm-outage-risk](https://github.com/UgoBruzadin/storm-outage-risk) · MIT License

::: footer
Data: U.S. DOE / Oak Ridge National Laboratory EAGLE-I power outage data ([doi:10.13139/ORNLNCCS/1975202](https://doi.org/10.13139/ORNLNCCS/1975202)); NOAA HRRR via [Open-Meteo](https://open-meteo.com) and the University of Utah HRRR archive on AWS; NOAA NCEI Storm Events; NWS warnings and SPC outlooks via the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu); USFS / NLCD Tree Canopy Cover; U.S. Census Bureau ACS and TIGER boundaries. Map tiles © OpenStreetMap contributors, © CARTO.

Ugo Bruzadin Nunes · [github.com/UgoBruzadin/storm-outage-risk](https://github.com/UgoBruzadin/storm-outage-risk) · MIT License
:::
