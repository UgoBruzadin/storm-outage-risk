"""Does tree canopy help the model, state by state? (docs/experiments.md, E24)

The story page's tree finding is a correlation: across counties, canopy goes with storm damage in some states
and not in others (Missouri +0.43, Illinois −0.10 in the first two). This asks the modelling question instead:
does knowing a county's canopy improve predictions there? The moving-window model (2 h ahead, no HRRR
forecasts) with and without the canopy features, over seeds, on the 2024 validation year (trained 2020–2023), two ways:

  pooled   one model trained on every state, scored on each state's counties separately
  state    a model trained and scored on one state only, so it can't borrow from the others

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
    # training sampled (data.sampled_years); the validation year scored in full, a state at a time
    train = data.sampled_years(THRESHOLD_PCT, TRAIN_YEARS, LEAD)
    train["state"] = train.region_fips.astype(str).str[:2].map(data.STATES)
    rows = []

    def record(setup, state, spec, seed, y, p):
        s = score(y, p)
        rows.append({"setup": setup, "state": state, "features": spec, "seed": seed, "onset_pr_auc": s["pr_auc"],
                     "event_rate": s["event_rate"], "n_rows": s["n_test"], "n_events": s["n_events"]})
        print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)

    pooled = {}
    for spec_name, spec in SPECS.items():
        features = data.resolve_features(spec)
        for seed in seeds:
            pooled[spec_name, seed] = models.build("xgboost", PARAMS | {"random_state": seed}).fit(
                train[features], train["y"], sample_weight=train["weight"])
            print(f"pooled model: {spec_name}, seed {seed}", flush=True)
    for fips, v in data.state_rows(THRESHOLD_PCT, VAL_YEAR, LEAD):
        state = data.STATES.get(fips, fips)
        t = train[train.state == state]
        for spec_name, spec in SPECS.items():
            features = data.resolve_features(spec)
            for seed in seeds:
                record("pooled", state, spec_name, seed, v["y"].to_numpy(),
                       pooled[spec_name, seed].predict_proba(v[features])[:, 1])
                fitted = models.build("xgboost", PARAMS | {"random_state": seed}).fit(
                    t[features], t["y"], sample_weight=t["weight"])
                record("state", state, spec_name, seed, v["y"].to_numpy(), fitted.predict_proba(v[features])[:, 1])
        del v

    out = pd.DataFrame(rows)
    table = out.pivot_table(index=["setup", "state", "seed"], columns="features", values="onset_pr_auc")
    table["effect of canopy"] = table["with canopy"] / table["without canopy"] - 1
    print(table.round(4).to_string())
    print(table.groupby(level=[0, 1])["effect of canopy"].agg(["mean", "min", "max"]).round(4).to_string())


if __name__ == "__main__":
    main()
