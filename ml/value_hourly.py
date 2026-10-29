"""What staging crews on each forecast was worth in 2025, for the moving-window model.

The same question and assumptions as ml/value.py (Berkeley Lab ICE outage costs, customer
mix, restoration cut and staging cost scenarios), with every input known at the decision:

  decision   every hour, about the 6 hours starting LEAD hours later (mart_study__region_1h)
  staging    an alert episode (consecutive alerted hours in one region) keeps a crew staged
             from LEAD hours after its first alert to 6 hours after its last decision window
             opens; it costs the staging price for every 6 hours of that span, rounded up
  ready      a new outage (a region crossing 5% from below) inside a staged span: its
             avoidable loss counts as saved
  rule       alert when probability x the region's average avoidable loss per new outage
             (2020–2024) >= the staging price, the same for every forecast and using no
             2025 outcomes; also scored at each forecast's best cutoff in hindsight

Usage: pixi run python -m ml.value_hourly
Writes ml/results/value_hourly_2025.csv.
"""
import duckdb
import numpy as np
import pandas as pd

from ml import data, models
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT
from ml.value import MIXES, RESTORATION_CUT, STAGING_COST, mix_cost

LEAD = 2
TRAIN_YEARS, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2025


def outages(years, db=data.DB):
    """New >= 5% outages per region: onset hour, customers affected (worst hour) and the average
    outage length per affected customer, from the onset hour through every following hour with
    >= 1% out (customer-hours = hourly peak customers out, summed)."""
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        WITH h AS (
            SELECT region_fips, hour, pct_out, pct_out * customers / 100 AS out,
                   lag(pct_out) OVER (PARTITION BY region_fips ORDER BY hour) AS before
            FROM marts.mart_study__region_1h
            WHERE year(hour) BETWEEN {min(years) - 1} AND {max(years)}
        ),
        runs AS (
            SELECT *, sum((coalesce(pct_out, 0) < 1)::INT) OVER (PARTITION BY region_fips ORDER BY hour) AS run
            FROM h
        ),
        onsets AS (
            SELECT region_fips, hour AS onset, run FROM runs
            WHERE pct_out >= {THRESHOLD_PCT} AND before < {THRESHOLD_PCT}
              AND year(hour) BETWEEN {min(years)} AND {max(years)}
        )
        SELECT o.region_fips, o.onset, max(r.out) AS affected, sum(r.out) AS customer_hours
        FROM onsets AS o
        JOIN runs AS r ON r.region_fips = o.region_fips AND r.run = o.run AND r.hour >= o.onset AND r.pct_out >= 1
        GROUP BY ALL
    """).df()
    con.close()
    df["minutes"] = 60 * df.customer_hours / df.affected.clip(lower=1)
    return df


def avoidable(ev, mix, cut):
    return ev.affected * (mix_cost(ev.minutes, mix) - mix_cost((1 - cut) * ev.minutes, mix))


def net_savings(test, flagged, events, saved, cost):
    """Staging cost of the alert episodes, and the avoidable loss of the outages they were ready for."""
    a = test.loc[flagged, ["region_fips", "block_start"]].sort_values(["region_fips", "block_start"])
    if a.empty:
        return 0.0, 0
    a["episode"] = (a.groupby("region_fips").block_start.diff() != pd.Timedelta(hours=1)).cumsum()
    spans = a.groupby("episode").agg(region_fips=("region_fips", "first"), first=("block_start", "min"),
                                     last=("block_start", "max"))
    spans["start"] = spans["first"] + pd.Timedelta(hours=LEAD)
    spans["end"] = spans["last"] + pd.Timedelta(hours=LEAD + 6)
    hours = (spans.end - spans.start) / pd.Timedelta(hours=1)
    staging = cost * np.ceil(hours / 6).sum()
    ready = events.reset_index(names="event").merge(spans[["region_fips", "start", "end"]], on="region_fips")
    ready = ready.loc[(ready.onset >= ready.start) & (ready.onset < ready.end), "event"].unique()
    return float(saved.loc[ready].sum() - staging), len(spans)


def main():
    df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR], LEAD)
    train, test = df[df.year.isin(TRAIN_YEARS)], df[df.year == TEST_YEAR].copy()
    cols = models.NEEDS_COLUMNS["official"]
    test["official"] = models.build("official").fit(train[cols], train["y"]).predict_proba(test[cols])[:, 1]
    features = data.resolve_features(FEATURES)
    fitted = models.build("xgboost", PARAMS).fit(train[features], train["y"])
    test["model"] = fitted.predict_proba(test[features])[:, 1]
    train_ev, test_ev = outages(TRAIN_YEARS), outages([TEST_YEAR]).reset_index(drop=True)
    rows = []
    for mix_name, mix in MIXES.items():
        for cut in RESTORATION_CUT:
            for cost in STAGING_COST:
                per_region = train_ev.assign(v=avoidable(train_ev, mix, cut)).groupby("region_fips").v.mean()
                expected = test.region_fips.map(per_region).fillna(per_region.mean())
                saved = avoidable(test_ev, mix, cut)
                row = {"mix": mix_name, "restoration_cut": cut, "staging_cost": cost,
                       "perfect": float(saved.sum() - cost * len(test_ev))}
                for name in ("model", "official"):
                    row[name], row[f"{name}_episodes"] = net_savings(test, test[name] * expected >= cost,
                                                                     test_ev, saved, cost)
                    # best cutoff in hindsight, over a ladder of cutoffs on the same score
                    score = test[name] * expected
                    ladder = np.unique(np.append(np.quantile(score, np.linspace(0.9, 0.9999, 25)), cost))
                    row[f"{name}_best"] = max(0.0, *(net_savings(test, score >= q, test_ev, saved, cost)[0]
                                                     for q in ladder))
                rows.append(row)
                print({k: round(v / 1e6, 2) if isinstance(v, float) and abs(v) > 1000 else v
                       for k, v in row.items()}, flush=True)
    pd.DataFrame(rows).to_csv(data.ROOT / "ml" / "results" / "value_hourly_2025.csv", index=False)


if __name__ == "__main__":
    main()
