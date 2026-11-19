# Results summary

Written by `ml/summary.py`. Before = the last commit's `ml/results/`.


## Headline, 2025

| | now | before |
|---|---|---|
| Counties | 3089 | 3089 |
| PR-AUC, model + five HRRR runs | 0.102 **changed** | 0.087 |
| PR-AUC, warnings + outlook | 0.022 | 0.022 |
| Ratio, model + five HRRR runs | 4.72× **changed** | 4.01× |
| Ratio, no forecasts | 2.97× **changed** | 2.67× |
| Ratio, perfect weather (ceiling) | 5.29× **changed** | 4.44× |

## Other test years

| | now | before |
|---|---|---|
| 2022, no forecasts | 2.94× **changed** | 2.51× |
| 2023, no forecasts | 2.69× **changed** | 2.45× |
| 2024, no forecasts | 3.48× **changed** | 2.91× |
| Counties never trained on (2025) | 2.59× **changed** | 2.13× |

## By state (ratio, 95% range in the file)

| | now | before |
|---|---|---|
| MO+IL, trained on all 48 | 3.00× **changed** | 2.77× |
| the other 46, trained on all 48 | 4.91× **changed** | 4.15× |
| all 48, trained on all 48 | 4.72× **changed** | 4.01× |
| AL, trained on all 48 | 3.99× **changed** | 2.97× |
| AZ, trained on all 48 | 3.24× **changed** | 2.74× |
| AR, trained on all 48 | 3.39× **changed** | 2.73× |
| CA, trained on all 48 | 4.31× **changed** | 3.57× |
| CO, trained on all 48 | 8.61× **changed** | 4.49× |
| DE, trained on all 48 | 2.74× **changed** | 2.00× |
| DC, trained on all 48 | 0.34× **changed** | 0.63× |
| FL, trained on all 48 | 7.07× **changed** | 4.61× |
| GA, trained on all 48 | 3.49× **changed** | 2.96× |
| ID, trained on all 48 | 4.88× **changed** | 3.67× |
| IL, trained on all 48 | 2.79× **changed** | 2.40× |
| IN, trained on all 48 | 2.91× **changed** | 2.51× |
| IA, trained on all 48 | 5.03× **changed** | 4.89× |
| KS, trained on all 48 | 5.50× **changed** | 3.38× |
| KY, trained on all 48 | 3.25× **changed** | 2.93× |
| LA, trained on all 48 | 3.30× **changed** | 2.79× |
| ME, trained on all 48 | 7.16× **changed** | 5.81× |
| MD, trained on all 48 | 1.75× **changed** | 1.71× |
| MA, trained on all 48 | 7.50× **changed** | 5.10× |
| MI, trained on all 48 | 4.47× **changed** | 4.16× |
| MN, trained on all 48 | 4.17× **changed** | 3.71× |
| MS, trained on all 48 | 4.90× **changed** | 3.67× |
| MO, trained on all 48 | 3.00× **changed** | 2.88× |
| MT, trained on all 48 | 3.48× **changed** | 1.83× |
| NE, trained on all 48 | 9.74× **changed** | 5.87× |
| NV, trained on all 48 | 4.86× **changed** | 5.17× |
| NH, trained on all 48 | 11.68× **changed** | 9.20× |
| NJ, trained on all 48 | 6.62× **changed** | 3.93× |
| NM, trained on all 48 | 6.65× **changed** | 4.00× |
| NY, trained on all 48 | 5.08× **changed** | 4.19× |
| NC, trained on all 48 | 4.50× **changed** | 4.24× |
| ND, trained on all 48 | 2.69× **changed** | 2.78× |
| OH, trained on all 48 | 3.03× **changed** | 2.93× |
| OK, trained on all 48 | 3.86× **changed** | 3.06× |
| OR, trained on all 48 | 6.38× **changed** | 4.45× |
| PA, trained on all 48 | 3.83× **changed** | 3.09× |
| RI, trained on all 48 | 2.63× **changed** | 4.14× |
| SC, trained on all 48 | 4.70× **changed** | 3.38× |
| SD, trained on all 48 | 4.21× **changed** | 3.41× |
| TN, trained on all 48 | 4.11× **changed** | 3.59× |
| TX, trained on all 48 | 4.45× **changed** | 4.02× |
| UT, trained on all 48 | 2.91× **changed** | 2.49× |
| VT, trained on all 48 | 4.47× **changed** | 5.75× |
| VA, trained on all 48 | 4.22× **changed** | 3.74× |
| WA, trained on all 48 | 4.46× **changed** | 2.88× |
| WV, trained on all 48 | 3.19× **changed** | 3.35× |
| WI, trained on all 48 | 5.71× **changed** | 5.34× |
| WY, trained on all 48 | 3.31× **changed** | 2.27× |

## Coverage (scored on all counties)

| | now | before |
|---|---|---|
| trained on all counties | 4.72× **changed** | 4.01× |
| trained on without under 5% | 4.66× **changed** | 3.89× |
| trained on without under 8% | 4.60× **changed** | 3.76× |

## Canopy in the model (PR-AUC change, 2024)

| | now | before |
|---|---|---|
| Alabama | +1.6% **changed** | -1.0% |
| Arizona | -1.6% **changed** | +3.3% |
| Arkansas | +0.4% **changed** | -2.4% |
| California | +1.2% **changed** | +3.0% |
| Colorado | -0.6% **changed** | +1.8% |
| Delaware | -4.6% **changed** | -9.3% |
| District of Columbia | -8.3% **changed** | -18.1% |
| Florida | +0.0% **changed** | +0.9% |
| Georgia | +0.3% **changed** | -1.1% |
| Idaho | +0.3% **changed** | +2.0% |
| Illinois | -1.5% **changed** | -1.4% |
| Indiana | -1.6% **changed** | -1.0% |
| Iowa | +1.0% **changed** | +3.3% |
| Kansas | -0.8% **changed** | +2.6% |
| Kentucky | -3.1% **changed** | +10.1% |
| Louisiana | +0.2% **changed** | +2.0% |
| Maine | +0.5% **changed** | +1.3% |
| Maryland | -1.4% **changed** | -6.5% |
| Massachusetts | +0.8% **changed** | -2.6% |
| Michigan | -1.9% **changed** | +2.9% |
| Minnesota | -5.9% **changed** | -0.6% |
| Mississippi | +1.9% **changed** | -0.6% |
| Missouri | +0.5% **changed** | -4.3% |
| Montana | +0.4% **changed** | +7.9% |
| Nebraska | -3.2% **changed** | +5.9% |
| Nevada | -0.0% **changed** | +5.4% |
| New Hampshire | +3.3% **changed** | +0.8% |
| New Jersey | -3.8% **changed** | +14.6% |
| New Mexico | -2.6% **changed** | +10.8% |
| New York | +1.4% **changed** | +2.4% |
| North Carolina | +0.4% **changed** | -0.3% |
| North Dakota | +0.9% **changed** | +1.3% |
| Ohio | +0.6% **changed** | -4.4% |
| Oklahoma | -1.7% **changed** | +3.7% |
| Oregon | -0.0% **changed** | +2.6% |
| Pennsylvania | -0.4% **changed** | +1.3% |
| Rhode Island | -0.9% **changed** | +1.3% |
| South Carolina | +1.6% **changed** | -4.1% |
| South Dakota | -1.5% **changed** | +14.5% |
| Tennessee | +0.3% **changed** | -7.2% |
| Texas | -1.1% **changed** | +2.2% |
| Utah | +2.6% **changed** | +4.2% |
| Vermont | +1.0% **changed** | +25.0% |
| Virginia | +1.2% **changed** | +3.9% |
| Washington | -1.6% **changed** | +8.9% |
| West Virginia | -1.0% **changed** | +11.3% |
| Wisconsin | -1.3% **changed** | +17.9% |
| Wyoming | +2.5% **changed** | -5.6% |

## A typical home's chance (2025)

| | now | before |
|---|---|---|
| Cross-entropy skill vs the usual month, model | +10.9% **changed** | +9.2% |
| Cross-entropy skill vs the usual month, warnings + outlook | -1.6% | -1.6% |

## Beyond the weather

| | now | before |
|---|---|---|
| Counties the outage data barely covers | 419 | 419 |
