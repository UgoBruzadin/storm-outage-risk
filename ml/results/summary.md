# Results summary

Written by `ml/summary.py`. Before = the last commit's `ml/results/`.


## Headline, 2025

| | now | before |
|---|---|---|
| Counties | 3089 **changed** | 490 |
| PR-AUC, model + five HRRR runs | 0.087 **changed** | 0.127 |
| PR-AUC, warnings + outlook | 0.022 **changed** | 0.036 |
| Ratio, model + five HRRR runs | 4.01× **changed** | 3.54× |
| Ratio, no forecasts | 2.67× **changed** | 2.11× |
| Ratio, perfect weather (ceiling) | 4.44× **changed** | 3.79× |

## Other test years

| | now | before |
|---|---|---|
| 2022, no forecasts | 2.51× **changed** | 2.67× |
| 2023, no forecasts | 2.45× **changed** | 2.13× |
| 2024, no forecasts | 2.91× **changed** | 2.31× |
| Counties never trained on (2025) | 2.13× **changed** | 1.75× |

## By state (ratio, 95% range in the file)

| | now | before |
|---|---|---|
| MO+IL, trained on all 48 | 2.77× | – |
| the other 46, trained on all 48 | 4.15× | – |
| all 48, trained on all 48 | 4.01× | – |
| AL, trained on all 48 | 2.97× | – |
| AZ, trained on all 48 | 2.74× | – |
| AR, trained on all 48 | 2.73× | – |
| CA, trained on all 48 | 3.57× | – |
| CO, trained on all 48 | 4.49× | – |
| DE, trained on all 48 | 2.00× | – |
| DC, trained on all 48 | 0.63× | – |
| FL, trained on all 48 | 4.61× | – |
| GA, trained on all 48 | 2.96× | – |
| ID, trained on all 48 | 3.67× | – |
| IL, trained on all 48 | 2.40× | – |
| IN, trained on all 48 | 2.51× | – |
| IA, trained on all 48 | 4.89× | – |
| KS, trained on all 48 | 3.38× | – |
| KY, trained on all 48 | 2.93× | – |
| LA, trained on all 48 | 2.79× | – |
| ME, trained on all 48 | 5.81× | – |
| MD, trained on all 48 | 1.71× | – |
| MA, trained on all 48 | 5.10× | – |
| MI, trained on all 48 | 4.16× | – |
| MN, trained on all 48 | 3.71× | – |
| MS, trained on all 48 | 3.67× | – |
| MO, trained on all 48 | 2.88× | – |
| MT, trained on all 48 | 1.83× | – |
| NE, trained on all 48 | 5.87× | – |
| NV, trained on all 48 | 5.17× | – |
| NH, trained on all 48 | 9.20× | – |
| NJ, trained on all 48 | 3.93× | – |
| NM, trained on all 48 | 4.00× | – |
| NY, trained on all 48 | 4.19× | – |
| NC, trained on all 48 | 4.24× | – |
| ND, trained on all 48 | 2.78× | – |
| OH, trained on all 48 | 2.93× | – |
| OK, trained on all 48 | 3.06× | – |
| OR, trained on all 48 | 4.45× | – |
| PA, trained on all 48 | 3.09× | – |
| RI, trained on all 48 | 4.14× | – |
| SC, trained on all 48 | 3.38× | – |
| SD, trained on all 48 | 3.41× | – |
| TN, trained on all 48 | 3.59× | – |
| TX, trained on all 48 | 4.02× | – |
| UT, trained on all 48 | 2.49× | – |
| VT, trained on all 48 | 5.75× | – |
| VA, trained on all 48 | 3.74× | – |
| WA, trained on all 48 | 2.88× | – |
| WV, trained on all 48 | 3.35× | – |
| WI, trained on all 48 | 5.34× | – |
| WY, trained on all 48 | 2.27× | – |

## Coverage (scored on all counties)

| | now | before |
|---|---|---|
| trained on all counties | 4.01× **changed** | 3.54× |
| trained on without under 5% | 3.89× **changed** | 3.40× |
| trained on without under 8% | 3.76× **changed** | 3.31× |

## Canopy in the model (PR-AUC change, 2024)

| | now | before |
|---|---|---|
| Alabama | -1.0% | – |
| Arizona | +3.3% | – |
| Arkansas | -2.4% | – |
| California | +3.0% | – |
| Colorado | +1.8% | – |
| Delaware | -9.3% | – |
| District of Columbia | -18.1% | – |
| Florida | +0.9% | – |
| Georgia | -1.1% | – |
| Idaho | +2.0% | – |
| Illinois | -1.4% **changed** | -3.9% |
| Indiana | -1.0% **changed** | +3.4% |
| Iowa | +3.3% **changed** | +2.4% |
| Kansas | +2.6% | – |
| Kentucky | +10.1% | – |
| Louisiana | +2.0% | – |
| Maine | +1.3% | – |
| Maryland | -6.5% | – |
| Massachusetts | -2.6% | – |
| Michigan | +2.9% **changed** | +6.2% |
| Minnesota | -0.6% | – |
| Mississippi | -0.6% | – |
| Missouri | -4.3% **changed** | -4.1% |
| Montana | +7.9% | – |
| Nebraska | +5.9% | – |
| Nevada | +5.4% | – |
| New Hampshire | +0.8% | – |
| New Jersey | +14.6% | – |
| New Mexico | +10.8% | – |
| New York | +2.4% | – |
| North Carolina | -0.3% | – |
| North Dakota | +1.3% | – |
| Ohio | -4.4% | – |
| Oklahoma | +3.7% | – |
| Oregon | +2.6% | – |
| Pennsylvania | +1.3% | – |
| Rhode Island | +1.3% | – |
| South Carolina | -4.1% | – |
| South Dakota | +14.5% | – |
| Tennessee | -7.2% | – |
| Texas | +2.2% | – |
| Utah | +4.2% | – |
| Vermont | +25.0% | – |
| Virginia | +3.9% | – |
| Washington | +8.9% | – |
| West Virginia | +11.3% | – |
| Wisconsin | +17.9% | – |
| Wyoming | -5.6% | – |

## A typical home's chance (2025)

| | now | before |
|---|---|---|
| Cross-entropy skill vs the usual month, model | +9.2% **changed** | +14.3% |
| Cross-entropy skill vs the usual month, warnings + outlook | -1.6% **changed** | +5.5% |

## Beyond the weather

| | now | before |
|---|---|---|
| Counties the outage data barely covers | 419 **changed** | 23 |
