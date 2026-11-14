"""Feature decisions for the moving-window model, on the validation year, over several seeds.

Trained on 2020–2023, scored on 2024 new outages at one lead (default 2 hours ahead), so the
choice never looks at the 2025 test year. Each configuration runs with every seed; a change
counts when it moves the score the same way for (nearly) every seed, as in seeds_ablate.yaml.

Usage: pixi run python -m ml.hourly_ablation [--lead 2] [--seeds 0,1,2,3,4] [--configs 0,1]
                                            [--train-start 2018] [--tag fresh]
Writes ml/results/hourly_ablation_lead<L>[_from<year>][_<tag>].csv.
"""
import argparse

import pandas as pd

from ml import data, models
from ml.metrics import score

# a record of an experiment on the Missouri + Illinois recipe: pinned to it (moving_window.FEATURES_V1)
from ml.moving_window import PARAMS_V1 as PARAMS
from ml.moving_window import THRESHOLD_PCT, predict_states

TRAIN_YEARS, VAL_YEAR = [2020, 2021, 2022, 2023], 2024
BASE = "weather+place+recent_now+warnings+outlook"
CONFIGS = {
    "base (weather, place, recent, official)": BASE,
    "+ neighbours": f"{BASE}+neighbors",
    "+ neighbours + time since last outage": f"{BASE}+neighbors+since",
    "+ neighbours + rain in the past 72 h": f"{BASE}+neighbors+wet_72h",
    "+ neighbours − canopy": f"{BASE}+neighbors-canopy",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead", type=int, default=2)
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--configs", help="indexes into CONFIGS, e.g. 0,1 (default: all)")
    parser.add_argument("--train-start", type=int, default=TRAIN_YEARS[0])
    parser.add_argument("--tag", default="", help="added to the results file name, e.g. fresh")
    args = parser.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    configs = dict(list(CONFIGS.items()) if args.configs is None
                   else [list(CONFIGS.items())[int(i)] for i in args.configs.split(",")])
    train_years = list(range(args.train_start, VAL_YEAR))
    train = data.sampled_years(THRESHOLD_PCT, train_years, args.lead)    # sampled; 2024 is scored in full
    fitted = {}
    for name, spec in configs.items():
        features = data.resolve_features(spec)
        for seed in seeds:
            fitted[name, seed] = (models.build("xgboost", PARAMS | {"random_state": seed}).fit(
                train[features], train.y, sample_weight=train.weight), features, None)
            print(f"fitted {name}, seed {seed}", flush=True)
    del train
    val = predict_states(fitted, VAL_YEAR, args.lead, keep=("y",))
    rows = []
    suffix = ("" if args.train_start == TRAIN_YEARS[0] else f"_from{args.train_start}") + \
        (f"_{args.tag}" if args.tag else "")
    out = data.ROOT / "ml" / "results" / f"hourly_ablation_lead{args.lead}{suffix}.csv"
    for name, spec in configs.items():
        for seed in seeds:
            s = score(val["y"].to_numpy(), val[name, seed].to_numpy())
            rows.append({"lead_hours": args.lead, "train_years": f"{train_years[0]}–{train_years[-1]}",
                         "config": name, "features": spec, "seed": seed,
                         "onset_pr_auc": s["pr_auc"], "precision_top1": s["precision_top1"],
                         "recall_top1": s["recall_top1"], "n_rows": len(val), "n_events": int(val["y"].sum())})
            print(rows[-1], flush=True)
            pd.DataFrame(rows).to_csv(out, index=False)
    result = pd.DataFrame(rows)
    table = result.pivot(index="config", columns="seed", values="onset_pr_auc").reindex(list(configs))
    base = table.iloc[0]
    summary = pd.DataFrame({"mean": table.mean(axis=1), "vs base": table.mean(axis=1) / base.mean() - 1,
                            "seeds better": (table.gt(base, axis=1)).sum(axis=1)})
    print(summary.round(4).to_string())


if __name__ == "__main__":
    main()
