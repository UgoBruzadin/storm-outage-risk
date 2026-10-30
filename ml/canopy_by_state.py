"""Does tree canopy help the model in Missouri, in Illinois, or both? (docs/experiments.md, E24)

The story page's tree finding is a correlation: across counties, canopy goes with storm damage in Missouri
(r = +0.43) and not in Illinois (−0.10). This asks the modelling question instead: does knowing a county's
canopy improve predictions there? The moving-window model (2 h ahead, no HRRR forecasts) with and without the
canopy features, over seeds, on the 2024 validation year (trained 2020–2023), two ways:

  pooled   one model trained on both states, scored on each state's counties separately
  state    a model trained and scored on one state only, so it can't borrow from the other

Usage: pixi run python -m ml.canopy_by_state [--seeds 0,1,2]
Writes ml/results/canopy_by_state.csv.
"""
import argparse

import pandas as pd

from ml import data, models
from ml.metrics import score
from ml.moving_window import FEATURES, PARAMS, THRESHOLD_PCT

TRAIN_YEARS, VAL_YEAR, LEAD = [2020, 2021, 2022, 2023], 2024, 2
SPECS = {"with canopy": FEATURES, "without canopy": f"{FEATURES}-canopy"}
OUT = data.ROOT / "ml" / "results" / "canopy_by_state.csv"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="0,1,2")
    seeds = [int(s) for s in parser.parse_args().seeds.split(",")]
    df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [VAL_YEAR], LEAD)
    df["state"] = df.region_fips.str[:2].map({"29": "Missouri", "17": "Illinois"})
    train, val = df[df.year.isin(TRAIN_YEARS)], df[df.year == VAL_YEAR]
    rows = []

    def record(setup, state, spec, seed, y, p):
        s = score(y, p)
        rows.append({"setup": setup, "state": state, "features": spec, "seed": seed, "onset_pr_auc": s["pr_auc"],
                     "event_rate": s["event_rate"], "n_rows": s["n_test"], "n_events": s["n_events"]})
        print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)

    for spec_name, spec in SPECS.items():
        features = data.resolve_features(spec)
        for seed in seeds:
            params = PARAMS | {"random_state": seed}
            pooled = models.build("xgboost", params).fit(train[features], train["y"])
            for state, v in val.groupby("state"):
                record("pooled", state, spec_name, seed, v["y"].to_numpy(), pooled.predict_proba(v[features])[:, 1])
            for state in ("Missouri", "Illinois"):
                t, v = train[train.state == state], val[val.state == state]
                fitted = models.build("xgboost", params).fit(t[features], t["y"])
                record("state", state, spec_name, seed, v["y"].to_numpy(), fitted.predict_proba(v[features])[:, 1])

    out = pd.DataFrame(rows)
    table = out.pivot_table(index=["setup", "state", "seed"], columns="features", values="onset_pr_auc")
    table["effect of canopy"] = table["with canopy"] / table["without canopy"] - 1
    print(table.round(4).to_string())
    print(table.groupby(level=[0, 1])["effect of canopy"].agg(["mean", "min", "max"]).round(4).to_string())


if __name__ == "__main__":
    main()
