# Results summary

Written by `ml/summary.py`. Before = the last commit's `ml/results/`.


## Headline, 2025

| | now | before |
|---|---|---|
| Counties | 490 **changed** | 216 |
| PR-AUC, model + five HRRR runs | 0.118 **changed** | 0.094 |
| PR-AUC, warnings + outlook | 0.030 **changed** | 0.039 |
| Ratio, model + five HRRR runs | 3.91× **changed** | 2.40× |
| Ratio, no forecasts | 2.39× **changed** | 1.63× |
| Ratio, perfect weather (ceiling) | 4.30× **changed** | 2.54× |

## Other test years

| | now | before |
|---|---|---|
| 2022, no forecasts | 2.67× **changed** | 1.83× |
| 2023, no forecasts | 2.13× **changed** | 1.66× |
| 2024, no forecasts | 2.31× **changed** | 2.06× |
| Counties never trained on (2025) | 1.75× **changed** | 1.45× |

## By state (ratio, 95% range in the file)

| | now | before |
|---|---|---|
| MO+IL, trained on all 7 | 2.92× | – |
| IN+IA+MI+MN+WI, trained on all 7 | 4.71× | – |
| all 7, trained on all 7 | 3.91× | – |
| IL, trained on all 7 | 2.58× | – |
| IN, trained on all 7 | 2.73× | – |
| IA, trained on all 7 | 4.08× | – |
| MI, trained on all 7 | 4.89× | – |
| MN, trained on all 7 | 4.49× | – |
| MO, trained on all 7 | 3.02× | – |
| WI, trained on all 7 | 5.44× | – |
| IN+IA+MI+MN+WI, trained on MO+IL only (never seen) | 3.09× | – |

## Coverage (scored on all counties)

| | now | before |
|---|---|---|
| trained on all counties | 3.54× | – |
| trained on without under 5% | 3.40× | – |
| trained on without under 8% | 3.31× | – |

## Canopy in the model (PR-AUC change, 2024)

| | now | before |
|---|---|---|
| Illinois | -3.9% **changed** | +3.0% |
| Indiana | +3.4% | – |
| Iowa | +2.4% | – |
| Michigan | +6.2% | – |
| Missouri | -4.1% **changed** | +0.4% |

## A typical home's chance (2025)

| | now | before |
|---|---|---|
| Cross-entropy skill vs the usual month, model | +14.3% | – |
| Cross-entropy skill vs the usual month, warnings + outlook | +5.5% | – |

## Beyond the weather

| | now | before |
|---|---|---|
| Counties the outage data barely covers | 23 **changed** | 10 |
