"""What staging repair crews on each forecast could have been worth in 2025, state by state (docs/value-plan.md).

Replaces ml/value_hourly.py's national dollars, whose two-state assumptions (a flat price per staged county, one US
customer mix, unlimited crews, one restoration cut) don't hold across the lower 48. Every input below is known
before 2025, except the 2025 outcomes being scored.

Per county (region) c in state s:
  crews_c      crews a staged outage needs: the county's average customers out at a new outage's worst hour,
               2020-2024, / CUSTOMERS_PER_CREW (at least 1)
  rate_s       one crew-hour: CREW_SIZE line workers at the state's mean wage (BLS OEWS 2025) / 2,080 hours,
               x LOADING (benefits, overtime, supervision), + TRUCK_LODGING, scaled by the state's price level (BEA)
  loss         what a new outage costs its customers: Berkeley Lab ICE models (ml/value.py), with the state's
               customer mix (EIA-861 2024: residential, commercial -> small C&I, industrial -> large C&I) and the
               county's household income relative to the US median (ACS 2024) in the residential model
  avoidable    loss(length) - loss((1 - cut) x length): what a staged crew saves if it shortens the outage by cut
  L_c          the county's average avoidable loss per new outage, 2020-2024 (state average where it had none)

The rule, the same for every forecast: stage county c at decision hour t when p x L_c >= crews_c x rate_s x 6.
The crew limit: a state has POOL_SHARE of its line workers free to stage, in crews of CREW_SIZE. When more
counties qualify in one hour than the pool can cover, the ones with the most expected value per crew go first.
A run of staged hours in a county is one spell: crews held from 2 hours after its first decision to 8 hours after
its last (the window), charged crews_c x rate_s per hour. A new outage is ready if its county was staged at a
decision whose window holds the onset hour (2 to 7 hours before it).

Two ledgers, kept apart:
  customers    avoidable losses of the outages a crew was ready for, minus nothing: they don't pay for staging
  utilities    pay the staging; get back the revenue of the customer-hours restored sooner (revenue per
               customer-hour from EIA-861). That revenue is a transfer from customers, so it isn't in the total.
  net          customers' avoided losses - staging cost: the value to society, as the two-state estimate measured it

Every result is per state; the lower-48 rows are sums of states. The restoration cut isn't known, so it runs over a
grid. Break-even: with staging planned for one cut, the cut crews must actually achieve for it to pay.

Usage: pixi run python -m ml.value_states   (needs ingest/fetch_value_inputs.py and the cached 2025 predictions)
Writes ml/results/value_states_2025.csv (every state, scenario, forecast and cut; avoided_if_<c> = what the same
staging would have avoided had crews saved c instead) and value_breakeven_2025.csv (planned cut -> the cut crews must
actually achieve for staging to pay).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from ml import data
from ml.value import ICE, ice_cost
from ml.value_hourly import outages

CACHE, RESULTS, PLACE = data.ROOT / "data" / "cache", data.ROOT / "ml" / "results", data.ROOT / "data" / "raw" / "place"
TRAIN_YEARS, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2025
LEAD, WINDOW = 2, 6

# assumptions: each one is a named scenario, never a hidden constant
CREW_SIZE = 4                             # line workers per crew
LOADING = 2.0                             # wage -> fully loaded cost (benefits, overtime, supervision)
TRUCK_LODGING = 60.0                      # $ per crew-hour for trucks, fuel, lodging and meals, at US price level
CUSTOMERS_PER_CREW = [1_000, 3_000]       # customers out per crew a staged outage needs
POOL_SHARE = [0.10, 0.25, None]           # share of a state's line workers free to stage; None = no limit (a check)
CUTS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50]   # share of outage length a staged crew saves
ICE_INCOME = 69_243                       # the ICE residential survey's average household income

FORECASTS = {"Model + five HRRR runs, calibrated": "p_cal", "Model + five HRRR runs": "p_mean",
             "Model, weather so far": "forecast-ready", "Warnings + outlook": "warnings + outlook",
             "Perfect foresight": "y"}


def state_inputs():
    s = pd.read_csv(PLACE / "value_state.csv", dtype={"state_fips": str}).set_index("state_fips")
    s["rate"] = CREW_SIZE * s.line_wage_mean / 2080 * LOADING + TRUCK_LODGING * s.rpp / 100
    total = s[["cust_res", "cust_com", "cust_ind"]].sum(axis=1)
    s["mix_res"], s["mix_com"], s["mix_ind"] = s.cust_res / total, s.cust_com / total, s.cust_ind / total
    s["revenue_per_customer_hour"] = s.utility_revenue / total / 8760
    s["customers"] = total
    return s


def region_income(regions):
    """Household income per region relative to the US median; a merged region averages its counties."""
    county = pd.read_csv(PLACE / "value_county.csv", dtype={"county_fips": str}).set_index("county_fips")
    us = pd.read_csv(PLACE / "value" / "acsdt5y2024-b19013.dat", sep="|", dtype=str).set_index("GEO_ID")
    us_median = float(us.loc["0100000US", "B19013_E001"])
    rel = {}
    for r in regions:
        values = [v for v in (county.median_hh_income.get(f) for f in r.split("+")) if pd.notna(v)]
        rel[r] = np.mean(values) / us_median if values else 1.0      # no ACS match (Connecticut's regions): US
    return pd.Series(rel)


def residential_cost(minutes, income):
    """ICE residential cost per customer with the household-income term at `income` instead of the survey mean."""
    d = np.minimum(np.asarray(minutes, float), 16 * 60)
    (pa, pb, pc, pr), (ga, gb, gc, gr) = ICE["residential"]["probit"], ICE["residential"]["glm"]
    pr, gr = pr + 2.340e-7 * (income - ICE_INCOME), gr + 1.653e-6 * (income - ICE_INCOME)
    return norm.cdf(pa + pb * d + pc * d**2 + pr) * np.exp(ga + gb * d + gc * d**2 + gr)


def outage_cost(ev, minutes):
    """Customer cost of each outage in `ev` if it lasted `minutes`: the state mix, the county's income."""
    income = ICE_INCOME * ev.rel_income.to_numpy()
    per_customer = (ev.mix_res * residential_cost(minutes, income) + ev.mix_com * ice_cost("small_ci", minutes)
                    + ev.mix_ind * ice_cost("large_ci", minutes))
    return ev.affected * per_customer


def prepare(ev, states, rel_income):
    ev = ev.assign(state_fips=ev.region_fips.str[:2])
    ev = ev.join(states[["mix_res", "mix_com", "mix_ind", "revenue_per_customer_hour"]], on="state_fips")
    return ev.assign(rel_income=ev.region_fips.map(rel_income).fillna(1.0))


def predictions():
    a = pd.read_parquet(CACHE / "forecast_test_2025_predictions.parquet",
                        columns=["region_fips", "block_start", "warnings + outlook", "forecast-ready"])
    b = pd.read_parquet(CACHE / "forecast_calibrated_2025.parquet",
                        columns=["region_fips", "block_start", "y", "p_mean", "p_cal"])
    return b.merge(a, on=["region_fips", "block_start"], how="inner")


def stage(cand, pool):
    """Candidates (one row per county-hour that passes the rule) -> the ones the state's crew pool can cover."""
    if pool is None:
        return cand
    cand = cand.sort_values(["state_fips", "block_start", "per_crew"], ascending=[True, True, False])
    used = cand.groupby(["state_fips", "block_start"]).crews.cumsum()
    return cand[used <= cand.pool]


def spells_cost(staged):
    """Staging cost of the spells (runs of consecutive staged hours per county): crews x rate x held hours."""
    if staged.empty:
        return 0.0, 0, 0.0
    s = staged.sort_values(["region_fips", "block_start"])
    new = s.groupby("region_fips").block_start.diff() != pd.Timedelta(hours=1)
    spell = new.cumsum()
    g = s.groupby(spell).agg(n=("block_start", "size"), crews=("crews", "first"), rate=("rate", "first"))
    held = g.n + WINDOW - 1                     # from first + 2 h to last + 8 h
    return float((g.crews * g.rate * held).sum()), len(g), float((g.crews * held).sum())


def ready(staged, ev):
    """Boolean per outage in `ev`: its county was staged at a decision whose window holds the onset."""
    hits = set()
    for offset in range(LEAD, LEAD + WINDOW):
        hits |= set(zip(staged.region_fips, staged.block_start + pd.Timedelta(hours=offset), strict=True))
    return np.array([(r, h) in hits for r, h in zip(ev.region_fips, ev.onset, strict=True)], dtype=bool)


def main():
    states = state_inputs()
    pred = predictions()
    pred["state_fips"] = pred.region_fips.str[:2]
    regions = pred.region_fips.unique()
    rel_income = region_income(regions)
    hist = prepare(outages(TRAIN_YEARS), states, rel_income)
    test = prepare(outages([TEST_YEAR]).reset_index(drop=True), states, rel_income)
    missing = sorted(set(pred.state_fips) - set(states.index))
    if missing:
        raise SystemExit(f"no state inputs for {missing}: run ingest/fetch_value_inputs.py")

    # what each 2025 outage's customers would avoid at every cut: for break-even, the plan stays fixed while the
    # cut crews actually achieve varies
    avoid_at = {c: (outage_cost(test, test.minutes) - outage_cost(test, (1 - c) * test.minutes)).to_numpy()
                for c in CUTS}
    rows = []
    for per_crew_customers in CUSTOMERS_PER_CREW:
        crews = np.maximum(1, np.ceil(hist.groupby("region_fips").affected.mean() / per_crew_customers))
        for cut in CUTS:
            hist_av = outage_cost(hist, hist.minutes) - outage_cost(hist, (1 - cut) * hist.minutes)
            L = hist.assign(v=hist_av).groupby("region_fips").v.mean()
            L_state = hist.assign(v=hist_av).groupby("state_fips").v.mean()
            test_av = avoid_at[cut]
            revenue_back = test.affected * cut * test.minutes / 60 * test.revenue_per_customer_hour
            base = pred[["region_fips", "block_start", "state_fips"]].copy()
            base["L"] = base.region_fips.map(L).fillna(base.state_fips.map(L_state)).to_numpy()
            base["crews"] = base.region_fips.map(crews).fillna(1.0).to_numpy()
            base["rate"] = base.state_fips.map(states.rate).to_numpy()
            shift = base.crews * base.rate * WINDOW
            for pool_share in POOL_SHARE:
                pool = (None if pool_share is None
                        else np.floor(states.line_workers * pool_share / CREW_SIZE).rename("pool"))
                for name, col in FORECASTS.items():
                    p = pred[col].to_numpy(dtype=float)
                    ok = p * base.L.to_numpy() >= shift.to_numpy()
                    cand = base[ok].assign(per_crew=(p[ok] * base.L[ok] - shift[ok]) / base.crews[ok])
                    if pool is not None:
                        cand = cand.join(pool, on="state_fips")
                    staged = stage(cand, pool)
                    is_ready = ready(staged, test)
                    for st, g in staged.groupby("state_fips"):
                        cost, n_spells, crew_hours = spells_cost(g)
                        m = (test.state_fips == st).to_numpy()
                        r = m & is_ready
                        rows.append(_row(name, per_crew_customers, pool_share, cut, st, states, cost, n_spells,
                                         crew_hours, test_av[r].sum(), revenue_back[r].sum(), int(r.sum()),
                                         int(m.sum())) | {f"avoided_if_{c:g}": avoid_at[c][r].sum() for c in CUTS})
                    for st in sorted(set(states.index) - set(staged.state_fips)):
                        m = (test.state_fips == st).to_numpy()
                        rows.append(_row(name, per_crew_customers, pool_share, cut, st, states, 0.0, 0, 0.0,
                                         0.0, 0.0, 0, int(m.sum())) | {f"avoided_if_{c:g}": 0.0 for c in CUTS})
            print(f"customers/crew {per_crew_customers}, cut {cut:.0%}: done", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "value_states_2025.csv", index=False, float_format="%.6g")
    breakeven(out).to_csv(RESULTS / "value_breakeven_2025.csv", index=False, float_format="%.4g")


def _row(name, per_crew_customers, pool_share, cut, st, states, cost, n_spells, crew_hours, avoided, revenue,
         n_ready, n_outages):
    customers = states.customers[st]
    return {"forecast": name, "customers_per_crew": per_crew_customers,
            "pool_share": "no limit" if pool_share is None else pool_share, "cut": cut,
            "state_fips": st, "state": states.state_abbr[st], "new_outages": n_outages, "ready": n_ready,
            "spells": n_spells, "crew_hours": crew_hours, "staging_cost": cost, "customers_avoided": avoided,
            "utility_revenue_back": revenue, "net": avoided - cost, "net_per_customer": (avoided - cost) / customers,
            "staging_per_customer_month": cost / customers / 12,
            "bill_res_month": states.bill_res_month[st]}


def breakeven(out):
    """Staging planned as if crews save `cut`: what share of outage length must they actually save for the
    customers' avoided losses to cover the staging? Per state, forecast and scenario, and summed over the lower 48.
    Interpolated on the CUTS grid; NaN when even the largest cut doesn't pay, or nothing was staged."""
    realized = np.array(CUTS)
    cols = [f"avoided_if_{c:g}" for c in CUTS]
    keys = ["forecast", "customers_per_crew", "pool_share", "cut"]
    lower48 = out.groupby(keys, as_index=False)[["staging_cost", "new_outages", "ready", *cols]].sum()
    both = pd.concat([out, lower48.assign(state="lower 48", state_fips="00")], ignore_index=True)
    rows = []
    for _, r in both.iterrows():
        gain = r[cols].to_numpy(dtype=float) - r.staging_cost
        if r.staging_cost == 0:
            be = np.nan
        elif gain[0] >= 0:
            be = realized[0]
        elif (gain < 0).all():
            be = np.nan
        else:
            i = int(np.flatnonzero(gain >= 0)[0])
            be = realized[i - 1] + (realized[i] - realized[i - 1]) * -gain[i - 1] / (gain[i] - gain[i - 1])
        rows.append({k: r[k] for k in [*keys, "state"]} | {"planned_cut": r.cut, "breakeven_cut": be,
                                                             "staging_cost": r.staging_cost, "ready": r.ready})
    return pd.DataFrame(rows).drop(columns="cut")

if __name__ == "__main__":
    main()
