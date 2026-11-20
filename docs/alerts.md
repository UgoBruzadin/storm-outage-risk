# County alerts: choosing the cut-off

What a county alert would have looked like in 2025, a year the model didn't train on. `ml/alert_counts.py` writes
`ml/results/alert_counts_2025.csv`; the alerts themselves are sent by `alerts/send.py` in storm-outage-live.

## The rule

- **One alert per storm.** A county is alerted when its chance reaches the cut-off. Hours above it 6 hours apart or
  less are the same alert; it is alerted again only after more than 6 hours below.
- **An alert is followed by an outage** when a new outage (5% or more of the county's customers, after a day with
  none) starts in the 6-hour window of any of its hours.
- **An outage had an alert** when the county was at or above the cut-off at any hour whose window held it.
- **Warning:** hours from the alert's start to the outage's start, for outages that had an alert.

## The numbers (2025)

The USA live model (`ml/train_live_usa.py`, trained on 2020-2024, fed the five HRRR runs) on 25.3 million
county-hours in 3,053 counties. Warnings + outlook at the same number of alert hours; their score has a few levels
only, so their alert counts don't match exactly; compare rows with similar alerts a year.

| Area | Cut-off | Alerts / county-year | Median county | 90th pct county | Followed by an outage | Outages that had one | Median warning | Official: alerts / county-year | Official: followed | Official: outages |
|---|---|---|---|---|---|---|---|---|---|---|
| USA | 0.02 | 47.8 | 34 | 98 | 10% | 54% | 10 h | 32.2 | 9% | 36% |
| USA | 0.03 | 34.1 | 24 | 70 | 12% | 47% | 9 h | 32.2 | 9% | 36% |
| USA | 0.05 | 22.0 | 16 | 46 | 15% | 38% | 8 h | 12.2 | 13% | 19% |
| USA | 0.07 | 16.2 | 11 | 34 | 17% | 33% | 7 h | 12.2 | 13% | 19% |
| USA | 0.10 | 11.5 | 8 | 25 | 20% | 28% | 7 h | 12.2 | 13% | 19% |
| USA | 0.15 | 7.4 | 5 | 17 | 25% | 22% | 7 h | 3.1 | 23% | 9% |
| USA | 0.20 | 5.2 | 3 | 12 | 28% | 17% | 6 h | 3.1 | 23% | 9% |
| USA | 0.30 | 2.9 | 2 | 7 | 35% | 12% | 6 h | 3.1 | 23% | 9% |
| MO + IL | 0.02 | 36.3 | 32 | 68 | 9% | 49% | 10 h | 37.4 | 9% | 47% |
| MO + IL | 0.03 | 25.8 | 23 | 48 | 11% | 43% | 9 h | 13.8 | 15% | 30% |
| MO + IL | 0.05 | 16.7 | 14 | 31 | 15% | 37% | 8 h | 13.8 | 15% | 30% |
| MO + IL | 0.07 | 12.4 | 11 | 24 | 17% | 32% | 7 h | 13.8 | 15% | 30% |
| MO + IL | 0.10 | 9.1 | 8 | 18 | 20% | 27% | 7 h | 4.4 | 26% | 17% |
| MO + IL | 0.15 | 6.1 | 5 | 12 | 25% | 22% | 7 h | 4.4 | 26% | 17% |
| MO + IL | 0.20 | 4.5 | 4 | 9 | 28% | 19% | 6 h | 1.5 | 42% | 9% |
| MO + IL | 0.30 | 2.5 | 2 | 5 | 37% | 13% | 6 h | 1.5 | 42% | 9% |

## What it means

- **Nationally, the model's alerts are better on both counts.** At about 12 alerts a year, 1 in 5 of the model's
  alerts is followed by an outage and it alerts 28% of outages; warnings + outlook, 1 in 8 and 19%. At about 3 a
  year: 35% and 12%, against 23% and 9%.
- **In Missouri and Illinois the edge per alert is small.** At about 4.5 alerts a year: 28% and 19% against 26% and
  17%. These are the states where the model's lead over the official forecasts is smallest (3.0x against 4.9x
  elsewhere), and where the official forecasts alert most sharply.
- **Most outages get no alert at any useful cut-off.** Alerting half of them takes about 40 alerts a year, 9 in 10
  false. An alert says the odds are several times the usual, not that an outage is likely.
- **The warning is useful:** a median 6-10 hours before the outage begins.

## The levels chosen (MO + IL, live-v1.1)

| Level | USA live model | Frozen MO + IL model | Alerts / county-year (MO + IL) | Followed by an outage | Outages that had one |
|---|---|---|---|---|---|
| Elevated | 0.10 | 0.083 | 9.1 | 20% | 27% |
| High | 0.20 | 0.170 | 4.5 | 28% | 19% |

A cut-off is a chance and belongs to one model. The frozen MO + IL model's cut-offs give the same alerts per
county-year in MO + IL as the USA live model at 0.10 and 0.20 (`level_for_rate`, on the frozen model's 2025
chances; in sample, since it trained on 2025, but the number of alerts depends only on the spread of its chances,
and its in-sample hit rates, 21% and 30%, are close to the held-out ones). When the USA model goes live, its levels
are 0.10 and 0.20 directly.
