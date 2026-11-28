# What forecasts could be worth, lower 48: the redesigned estimate

Status (2026-11-26): steps 1–4 are built (`ingest/fetch_value_inputs.py`, `ml/value_states.py`); steps 5–7 are next.
Nothing from it is on the site yet.

## Why the old estimate had to go

The two-state dollar estimate (`ml/value_hourly.py`) doesn't scale to the country. Run on the lower 48 it gives
$130 M to $1.18 B in 2025 for the model without forecasts, and −$301 M to +$505 M for warnings + outlook
(`ml/results/value_hourly_2025.csv`, typical mix). The arithmetic isn't wrong. The two-state assumptions are applied
where they don't fit:

| Old assumption | Why it fails for 3,108 counties | Redesign |
|---|---|---|
| Staging costs $5,000 or $20,000 per county per 6 hours, whatever the county | Los Angeles County (3.76 M customers tracked, `data/app/regions.parquet`) and the median county (12,900) cost the same to cover | Cost scales with the job: crews needed × the state's crew-hour cost |
| The US customer mix everywhere | Almost all the value is businesses' outage costs, so the mix decides the answer | Each state's mix from EIA-861 2024 |
| One household income in the cost model | The ICE residential model takes income as an input; it was held at the survey's $69,243 | Each county's income relative to the US median (ACS 2024) |
| Unlimited crews | The old rule staged 5,000–88,000 spells nationwide, depending on the scenario | A crew pool per state, from its line workers (BLS) |
| A staged crew shortens outages by 10% or 25% | Nobody has measured it, here or in the cited literature | A grid of cuts, and each state's break-even cut |
| One national total | Hides where the value is, and where it's negative | States are the unit; the national row is their sum |

## The calculation

For each county *c* in state *s*, with every input known before 2025:

| Quantity | How it's computed | Source |
|---|---|---|
| Crew-hour cost, *rate_s* | 4 line workers × state mean wage ÷ 2,080 h × 2.0 loading, + $60 trucks and lodging × state price level ÷ 100 | BLS OEWS May 2025 (SOC 49-9051); BEA Regional Price Parities 2024 |
| Crews a staged outage needs, *crews_c* | the county's average customers out at a new outage's worst hour, 2020–2024, ÷ customers per crew (at least 1) | EAGLE-I; customers per crew is a scenario |
| Crew pool, *pool_s* | state line workers × share free to stage ÷ 4 | BLS OEWS; the share is a scenario |
| What an outage costs customers | ICE models with the state's customer mix and the county's relative income | Berkeley Lab ICE; EIA-861 2024; ACS 2024 |
| Avoidable loss | cost(length) − cost((1 − cut) × length) | cut is a grid |
| *L_c* | the county's average avoidable loss per new outage, 2020–2024 | |
| Revenue per customer-hour | the state's retail revenue ÷ customers ÷ 8,760 | EIA-861 2024 |

**The rule** (the same for every forecast): stage county *c* at hour *t* when *p* × *L_c* ≥ *crews_c* × *rate_s* × 6.
When more counties qualify in one hour than the state's pool can cover, the ones with the most expected value per crew
go first. A run of staged hours is one spell. It holds its crews from 2 hours after the first decision to 8 hours after
the last, and is charged *crews_c* × *rate_s* per hour. A crew is ready for a new outage if its county was staged at a
decision whose window holds the onset hour.

**Two ledgers, kept apart:**

| Ledger | Counts |
|---|---|
| Customers | the avoidable losses of the outages a crew was ready for |
| Utilities | pay the staging cost; get back the revenue of the customer-hours restored sooner |
| Net (society) | customers' avoided losses − staging cost. The revenue is a transfer from customers to utilities, so it isn't added |

For each state the output also includes net value per customer, the staging cost per customer per month (what it would
add to bills if a utility recovered it through rates), and the average residential bill.

**Scenarios:** customers per crew 1,000 or 3,000; pool 10% or 25% of line workers, or no limit (a check);
cut 2, 5, 10, 15, 20, 25, 35 and 50%. Forecasts: the model with five HRRR runs (raw and calibrated on 2024), the model
with weather so far, warnings + outlook, and perfect foresight. Outputs: `ml/results/value_states_2025.csv` (every
row) and `value_breakeven_2025.csv` (per state, forecast and scenario).

## First look (one scenario, before review)

Cut 10%, 1,000 customers per crew, pool 10% of line workers, lower 48 summed over states:

| Forecast | Outages a crew was ready for | Staging cost | Customers' avoided losses | Net |
|---|---|---|---|---|
| Perfect foresight | 24,501 | $275 M | $1,330 M | $1,056 M |
| Model + five HRRR runs, calibrated | 4,243 | $229 M | $458 M | $229 M |
| Model + five HRRR runs, raw | 5,102 | $299 M | $499 M | $201 M |
| Model, weather so far | 3,024 | $194 M | $276 M | $81 M |
| Warnings + outlook | 248 | $60 M | $197 M | $137 M |

What it shows, before any of it is checked:

- **The value is in a few huge outages.** Warnings + outlook had crews ready for only 248 outages but avoided
  $197 M, about $800,000 each, against about $108,000 for the model's. They stage in a few big metro counties where
  one outage is enormous. A national total over a year like this rests on a handful of storms, so it needs storm-day
  ranges before it can be quoted (step 5).
- **The crew limit rarely binds at 10%.** Removing it adds about 8% more ready outages for the model.
- **Calibration helps the dollars.** The calibrated model stages less and nets more than the raw one.
- **The model is negative in 9 of 49 states** at this scenario, Louisiana most.

### Break-even (full grid, pool 10% of line workers)

Staging is planned as if crews shorten outages by 10% (or 25%). The table gives how much they must actually shorten
them for customers' avoided losses to cover the staging, lower 48 summed (`ml/results/value_breakeven_2025.csv`):

| Forecast | Planned for 10% | Planned for 25% |
|---|---|---|
| Model + five HRRR runs, calibrated | 4.4–5.1% | 10.0–11.6% |
| Model + five HRRR runs, raw | 4.9–6.1% | 10.2–12.7% |
| Model, weather so far | 5.6–7.1% | 11.6–14.4% |
| Warnings + outlook | 3.2–5.4% | 13.9–15.2% |
| Perfect foresight | ≤ 2% | ≤ 2% |

Ranges are over 1,000 and 3,000 customers per crew. "≤ 2%" means it already pays at the smallest cut on the grid.

By state (planned for 10%, 1,000 customers per crew), the calibrated model stages in 44 states and pays off within
the planned 10% in 37 of them; the median state needs 5.9%. Warnings + outlook stage in 23 states and pay off within
10% in 12. Nevada needs 37% (one outage ready), and Massachusetts and South Dakota about 14%.

Read it as: planned for 10%, staging on the model pays for itself if crews shorten outages by about 5% or more. The
official forecasts look as good nationally when planned for 10%, because they stage rarely and only where the stakes
are largest. Planned for 25%, they stage more widely and need 14–15%, against 10–12% for the model.

## Next steps

5. **Storm-day ranges** for every state and the national sum, as the scores get, and a paired comparison of model vs
   warnings + outlook. Until then, no dollar figure is publishable.
6. **Check on two states.** Run on Missouri + Illinois and explain the difference from the published $1–24 M, one
   changed assumption at a time.
7. **County mix** from EIA-861 `Service_Territory` (state mix today), and the ICE large C&I size from MWh per
   industrial customer (national survey average today: TN's 23,000 MWh per industrial customer is far outside the
   survey's range, so this needs a cap).

## Known simplifications

- ICE dollars are used as the models give them, not inflated to 2025; wages are 2025 dollars. Both sides of the
  ledger should be in one dollar year before publishing.
- The pool is checked at each decision hour, not over the whole time a spell holds its crews.
- Commercial customers are treated as ICE small C&I and industrial as medium/large C&I. ICE splits at 50 MWh a year,
  which EIA's sectors don't.
- Crews per outage uses customers out at the worst hour; real restoration depends on how many places the lines broke.

## Decisions for the user

1. **Per state or per utility** for the crew pool? Per utility is closer to reality but needs EIA-861 territories
   joined to every decision.
2. **Crew assumptions.** 4 per crew, 2.0 loading, $60 per crew-hour for trucks and lodging, 1,000 or 3,000 customers
   per crew. Is there a figure you trust (mutual-assistance rates, a PUC filing)?
3. **County maps,** or states only? County values rest on a few outages each.

## Not in scope

Utility-side savings beyond revenue (overtime avoided, regulatory penalties), outages under 5% of a county's
customers, and anything that needs utility data this project doesn't have.
