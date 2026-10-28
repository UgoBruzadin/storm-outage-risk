"""What would acting on each forecast have been worth in the test year?

A utility can stage a crew in a county before a storm. Staging costs money every time;
it pays off only when the county then loses power, because restoration starts sooner.
Every forecast (this model, NWS warnings, the SPC outlook, both, the historical average)
is scored on the same new outages (onsets, >= 5% of customers) in 2025, two ways:

1. Relative economic value (the cost-loss model used to value weather forecasts): with
   staging cost C and avoidable loss L, act when the forecast probability >= C/L. Value is
   the share of a perfect forecast's savings the forecast captures, over the better of
   "never stage" and "always stage" (0 = no better than that, 1 = perfect). No dollar
   figures needed: one curve per forecast over C/L.

2. Dollars, under stated assumptions:
   - what an outage costs customers: Berkeley Lab's ICE Calculator models (residential,
     small and medium/large commercial & industrial), as a function of outage length
   - customer mix: residential / small C&I / medium-large C&I shares of customers
   - restoration_cut: the share of each outage's length that a staged crew cuts
   - staging_cost: dollars per staged county per 6-hour period
   A forecast's rule is the same for all of them and uses no 2025 outcomes: stage when
   probability x the county's average avoidable loss per new outage (2020–2024) >= staging cost.
   As a generous check, each forecast is also scored at its best cutoff in hindsight
   (chosen on 2025 itself), the most any rule on that forecast could have saved.

The official baselines are rate tables fitted on 2020–2024 new-outage periods only, so their
probabilities are calibrated for the question asked (fitted on every period, they carry the
higher rates of counties already out and over-stage).

Every number here is an upper bound in one more way than the model's scores: the model's
weather inputs are close to observed weather (README, "Limits").

Usage: pixi run python -m ml.value
Writes ml/results/value_2025.csv (dollar scenarios) and value_curves_2025.csv.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from ml import data, models

THRESHOLD_PCT = 5
TRAIN_YEARS, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2025
RESULTS = data.ROOT / "ml" / "results"
FORECASTS = ["climatology", "nws_warnings", "spc_outlook", "official"]     # plus the model, from data/app

# ICE Calculator econometric models (Schellenberg & Larsen, "Changes to the Underlying Econometric
# Models for the ICE Calculator", Berkeley Lab / Nexant): cost per interruption = P(any cost) from
# the probit x cost if any from the GLM (log link). Duration in minutes; every other variable at
# the survey average the report lists. Duration is capped at 16 hours, the range the surveys asked about.
ICE = {
    "residential": dict(
        probit=(-0.053, 0.002, -6.735e-7, 0.224 * .734 - 0.255 * .488 - 0.083 * .291 + 0.130 * 2.4 + 2.340e-7 * 69243),
        glm=(1.299, 0.002, -9.474e-7, 0.237 * .734 - 0.291 * .488 - 0.096 * .291 + 0.262 * 2.4 + 1.653e-6 * 69243)),
    "small_ci": dict(
        probit=(-1.332, 0.003, -1.783e-6, 0.215 * .893 + 0.537 * .455 + 0.664 * .376 + 0.124 * 2.6 + 0.082 * .271
                + 0.272 * .035 + 0.261 * .046 + 0.176 * .078),
        glm=(7.000, 0.004, -2.155e-6, -0.384 * .893 - 0.057 * .455 - 0.032 * .376 + 0.069 * 2.6 + 0.308 * .271
             + 0.538 * .035 + 0.786 * .046 + 0.587 * .078)),
}
LARGE_MWH = 6.6           # ln(annual MWh) average for medium/large C&I, which interacts with duration


def ice_cost(kind, minutes):
    """Dollars per customer for one interruption of `minutes`."""
    d = np.minimum(np.asarray(minutes, float), 16 * 60)
    if kind == "large_ci":
        m = LARGE_MWH
        z = (-1.082 + 0.005 * d - 2.689e-6 * d**2 + 0.380 * .865 + 0.118 * m - 3.183e-4 * d * m
             + 1.481e-7 * d**2 * m + 0.203 * .233 + 0.024 * 6.93)
        g = (4.916 + 0.005 * d - 2.912e-6 * d**2 + 0.032 * .865 + 0.489 * m - 1.270e-4 * d * m
             + 1.071e-7 * d**2 * m + 0.818 * .233 + 0.073 * 6.93)
    else:
        (pa, pb, pc, pr), (ga, gb, gc, gr) = ICE[kind]["probit"], ICE[kind]["glm"]
        z, g = pa + pb * d + pc * d**2 + pr, ga + gb * d + gc * d**2 + gr
    return norm.cdf(z) * np.exp(g)


def mix_cost(minutes, mix):
    return sum(share * ice_cost(kind, minutes) for kind, share in mix.items())


# customer mix: residential only (the floor), and roughly the US mix by customer count
# (EIA: about 88% residential, 12% commercial and industrial, most of it small)
MIXES = {"residential only": {"residential": 1.0},
         "typical mix": {"residential": 0.88, "small_ci": 0.11, "large_ci": 0.01}}
RESTORATION_CUT = [0.10, 0.25]            # share of outage length a staged crew saves
STAGING_COST = [5_000, 20_000]            # dollars per staged county per 6-hour period


def events(df):
    """Each new outage (onset at >= THRESHOLD_PCT): customers affected and the average outage length.
    The outage runs from the onset block through every following block with >= 1% out, the
    scorecard's event rule; customer-hours are mean customers out x 6 hours per block."""
    df = df.sort_values(["region_fips", "block_start"])
    on = df["peak_pct_out"] >= 1
    gap = df.groupby("region_fips")["block_start"].diff() != pd.Timedelta(hours=6)
    run = (~on | gap).groupby(df["region_fips"]).cumsum()      # a new run id after every break
    df = df.assign(run=run)
    onsets = df[df.is_onset & (df.y == 1)]
    rows = []
    for (region, r), g in df[on].groupby(["region_fips", "run"]):
        starts = onsets[(onsets.region_fips == region) & (onsets.run == r)]
        for idx, s in starts.iterrows():
            after = g[g.block_start >= s.block_start]
            hours = 6 * after["mean_out"].fillna(0).sum()
            affected = max(after["peak_out"].max(), 1)
            rows.append({"index": idx, "affected": affected, "minutes": 60 * hours / affected})
    return pd.DataFrame(rows).set_index("index")


def avoidable(ev, mix, cut):
    """Customer losses a staged crew avoids on each outage: the cost of its full length minus the
    cost of the length cut by `cut`, for every customer affected."""
    return ev.affected * (mix_cost(ev.minutes, mix) - mix_cost((1 - cut) * ev.minutes, mix))


def relative_value(p, y, alphas):
    """Richardson's relative economic value of acting when p >= alpha, for each cost/loss ratio alpha."""
    s = y.mean()
    out = []
    for a in alphas:
        act = p >= a
        hit, false = (act & (y == 1)).sum() / max((y == 1).sum(), 1), (act & (y == 0)).sum() / max((y == 0).sum(), 1)
        climate = min(a, s)                                   # expense of the better fixed strategy
        expense = false * a * (1 - s) - hit * s * (1 - a) + s
        out.append((climate - expense) / (climate - s * a))
    return np.array(out)


def main():
    df = data.load(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR])
    train, test = df[df.year.isin(TRAIN_YEARS)], df[df.year == TEST_YEAR].copy()
    train_onsets = train[train.is_onset]
    for name in FORECASTS:
        cols = models.NEEDS_COLUMNS[name]
        fitted = models.build(name).fit(train_onsets[cols], train_onsets["y"])
        test[name] = fitted.predict_proba(test[cols])[:, 1]
    preds = pd.read_parquet(data.ROOT / "data" / "app" / "predictions.parquet")[["region_fips", "block_start", "prob"]]
    test = test.merge(preds.rename(columns={"prob": "model"}), on=["region_fips", "block_start"], how="left")
    if test["model"].isna().any():
        raise ValueError("data/app/predictions.parquet doesn't cover the test year: run pixi run export-app")
    names = ["model", *FORECASTS]

    # 1. relative economic value on new outages
    onsets = test[test.is_onset]
    alphas = np.round(np.geomspace(0.002, 0.5, 40), 4)
    curves = pd.DataFrame({"cost_loss": alphas} | {n: relative_value(onsets[n].to_numpy(), onsets.y.to_numpy(), alphas)
                                                   for n in names})
    curves.to_csv(RESULTS / "value_curves_2025.csv", index=False)

    # 2. dollars
    train_ev, test_ev = events(train), events(test)
    scenarios = []
    for mix_name, mix in MIXES.items():
        for cut in RESTORATION_CUT:
            for cost in STAGING_COST:
                # the county's average avoidable loss per new outage, 2020–2024 (all counties' mean if none)
                per_county = train.loc[train_ev.index, ["region_fips"]].assign(v=avoidable(train_ev, mix, cut))
                county_mean = per_county.groupby("region_fips").v.mean()
                expected = onsets.region_fips.map(county_mean).fillna(per_county.v.mean())
                saved = pd.Series(0.0, index=onsets.index)
                saved[test_ev.index] = avoidable(test_ev, mix, cut)
                row = {"mix": mix_name, "restoration_cut": cut, "staging_cost": cost,
                       "outage_cost_2025": float((test_ev.affected * mix_cost(test_ev.minutes, mix)).sum()),
                       "perfect": float(saved.sum() - cost * (onsets.y == 1).sum())}
                for n in names:
                    act = onsets[n] * expected >= cost
                    row[n] = float(saved[act].sum() - cost * act.sum())
                    row[f"{n}_staged"] = int(act.sum())
                    # best cutoff in hindsight: stage the top k by expected saving, best k (ties staged together)
                    rank = (onsets[n] * expected).rename("score").to_frame().assign(net=saved - cost)
                    by_score = rank.groupby("score").net.sum().sort_index(ascending=False).cumsum()
                    row[f"{n}_best"] = float(max(0.0, by_score.max()))
                scenarios.append(row)
    result = pd.DataFrame(scenarios)
    result.to_csv(RESULTS / "value_2025.csv", index=False)
    pd.set_option("display.width", 200)
    print(f"{len(test_ev)} new outages in {TEST_YEAR}, {len(onsets):,} county-periods with no outage under way")
    print(curves.iloc[::4].round(3).to_string(index=False))
    show = result[["mix", "restoration_cut", "staging_cost", "perfect", *names]].copy()
    for c in ["perfect", *names]:
        show[c] = (show[c] / 1e6).round(2)
    print("\nnet savings vs never staging, $ millions:\n" + show.to_string(index=False))
    best = result[["mix", "restoration_cut", "staging_cost"]].copy()
    for n in names:
        best[n] = (result[f"{n}_best"] / 1e6).round(2)
    print("\nat each forecast's best cutoff in hindsight, $ millions:\n" + best.to_string(index=False))
    print("\ncustomer cost of 2025's new outages, $ millions:",
          result.groupby("mix").outage_cost_2025.first().div(1e6).round(1).to_dict())


if __name__ == "__main__":
    main()
