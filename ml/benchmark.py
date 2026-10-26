"""Run a benchmark config: every model x hyperparameters x feature set x split.

    pixi run benchmark ml/benchmarks/quick.yaml            # run it
    pixi run benchmark ml/benchmarks/quick.yaml --dry-run  # just list the runs
    pixi run benchmark ml/benchmarks/full.yaml --models lightgbm,xgboost

A config (YAML) says what to compare — see ml/benchmarks/quick.yaml:

    data:      threshold_pct (one or a list), years, train_on (all | onsets, one or a list)
    splits:    list of {kind: time|county|random, ...options}
    features:  feature-set specs, e.g. weather+place-canopy (groups in ml/data.py)
    models:    list of {name, params: {hyperparameter: value or [values to try]},
                        features: optional override}
    final:     the model export_app_data.py trains for the dashboard

Every run is logged to MLflow (experiment "benchmark/<name>"; `pixi run mlflow-ui`)
with the same metrics (ml/metrics.py), and the whole benchmark is written to
ml/results/benchmark_<name>.csv plus a readable leaderboard_<name>.md.
Baseline models (prior, climatology) don't use features: they run once per split.

Every run is scored twice: on all test blocks, and on ONSETS only (onset_* metrics) —
blocks whose previous 6 hours weren't already an event. Outages persist, so "it's out
now, it'll be out next block" scores well on all blocks without predicting anything new;
onsets are what early warning is about. Leaderboards rank by `rank_by` (default
onset_pr_auc).
"""
import argparse
import itertools
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ml import data, models, splits
from ml.metrics import score

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "ml" / "results"
TRACKING_URI = f"sqlite:///{ROOT / 'data' / 'mlflow.db'}"
ARTIFACTS = (ROOT / "data" / "mlruns").as_uri()
BASELINES = {"prior", "climatology"}


def expand_grid(params):
    """{'a': [1, 2], 'b': 3} -> [{'a': 1, 'b': 3}, {'a': 2, 'b': 3}]"""
    params = params or {}
    keys = list(params)
    values = [v if isinstance(v, list) else [v] for v in params.values()]
    return [dict(zip(keys, combo, strict=True)) for combo in itertools.product(*values)] or [{}]


def as_list(value):
    return value if isinstance(value, list) else [value]


def plan(config):
    """Every run the config asks for, as a list of dicts."""
    runs = []
    for threshold in as_list(config["data"]["threshold_pct"]):
        for train_on in as_list(config["data"].get("train_on", "all")):
            for split in config["splits"]:
                for entry in config["models"]:
                    feature_sets = ["-"] if entry["name"] in BASELINES else entry.get("features", config["features"])
                    for features in feature_sets:
                        for params in expand_grid(entry.get("params")):
                            runs.append({"threshold_pct": threshold, "train_on": train_on, "split": split,
                                         "model": entry["name"], "features": features, "params": params})
    return runs


def evaluate(df, run):
    """Pooled out-of-sample probabilities over the split's folds, scored on all blocks and on onsets.

    `df` must already be labeled for run["threshold_pct"] (data.label). With
    train_on = onsets, the model only ever sees onset rows — a model of new outages.
    """
    feature_cols = models.NEEDS_COLUMNS.get(run["model"], []) if run["features"] == "-" \
        else data.resolve_features(run["features"])
    kind = run["split"]["kind"]
    options = {k: v for k, v in run["split"].items() if k != "kind"}
    proba = np.full(len(df), np.nan)
    start = time.time()
    onset = df["is_onset"].to_numpy()
    for _, train_idx, test_idx in splits.make_splits(df, kind, **options):
        if run.get("train_on", "all") == "onsets":
            train_idx = train_idx[onset[train_idx]]
        model = models.build(run["model"], run["params"])
        model.fit(df.iloc[train_idx][feature_cols], df.iloc[train_idx]["y"])
        proba[test_idx] = model.predict_proba(df.iloc[test_idx][feature_cols])[:, 1]
    y, tested = df["y"].to_numpy(), ~np.isnan(proba)
    all_blocks = score(y[tested], proba[tested])
    onsets = score(y[tested & onset], proba[tested & onset])
    return {**all_blocks, **{f"onset_{k}": v for k, v in onsets.items()}, "fit_seconds": time.time() - start}


def split_label(split):
    extra = ",".join(f"{k}={v}" for k, v in split.items() if k != "kind")
    return f"{split['kind']}({extra})" if extra else split["kind"]


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def leaderboard(results, rank_by="onset_pr_auc"):
    """Markdown: one table per threshold x split, best first, baselines included for reference."""
    lines = []
    for (threshold, split), group in results.groupby(["threshold_pct", "split"], sort=False):
        lines += [f"\n### >= {threshold:g}% out · {split} · ranked by {rank_by}\n",
                  f"Event rate: {group.event_rate.iloc[0]:.2%} of all blocks, "
                  f"{group.onset_event_rate.iloc[0]:.2%} of onset blocks.\n",
                  "| rank | model | train on | features | params | onset PR-AUC | onset lift | onset prec@top1% "
                  "| all PR-AUC | all lift | all ROC-AUC |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for rank, r in enumerate(group.sort_values(rank_by, ascending=False).itertuples(), 1):
            lines.append(f"| {rank} | {r.model} | {r.train_on} | {r.features} | {r.params} | {r.onset_pr_auc:.3f} "
                         f"| {r.onset_pr_auc_lift:.1f}x | {r.onset_precision_top1:.1%} | {r.pr_auc:.3f} "
                         f"| {r.pr_auc_lift:.1f}x | {r.roc_auc:.3f} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="list the runs without training")
    parser.add_argument("--models", help="comma-separated subset of model names to run")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text())
    name = config["name"]
    runs = plan(config)
    if args.models:
        keep = set(args.models.split(","))
        runs = [r for r in runs if r["model"] in keep]
    print(f"benchmark {name!r}: {len(runs)} runs")
    if args.dry_run:
        for r in runs:
            print(f"  >={r['threshold_pct']}% {r['train_on']:6s} {split_label(r['split']):40s} {r['model']:13s} "
                  f"{r['features']:28s} {r['params']}")
        return

    import mlflow  # here, not at the top: tests and CI import this module without MLflow installed

    base = data.load(None, config["data"]["years"])
    labeled = {}
    for threshold in as_list(config["data"]["threshold_pct"]):
        labeled[threshold] = data.label(base, threshold)
        d = labeled[threshold]
        print(f">= {threshold}%: {len(d):,} region-blocks, {d.y.sum():,} events ({d.y.mean():.2%}); "
              f"{d.is_onset.sum():,} onset blocks with {d.y[d.is_onset].sum():,} new events")

    mlflow.set_tracking_uri(TRACKING_URI)
    experiment = f"benchmark/{name}"
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=ARTIFACTS)
    mlflow.set_experiment(experiment)
    commit = git_commit()

    rows = []
    for i, run in enumerate(runs, 1):
        label = split_label(run["split"])
        with mlflow.start_run(run_name=f">={run['threshold_pct']}%/{run['train_on']}/{label}/{run['model']}"
                                       f"/{run['features']}"):
            scores = evaluate(labeled[run["threshold_pct"]], run)
            mlflow.set_tags({"config": str(args.config.relative_to(ROOT) if args.config.is_absolute()
                                          else args.config), "git_commit": commit})
            mlflow.log_params({"split": label, "model": run["model"], "features": run["features"],
                               "threshold_pct": run["threshold_pct"], "train_on": run["train_on"],
                               "years": str(config["data"]["years"]),
                               **{f"hp.{k}": v for k, v in run["params"].items()}})
            mlflow.log_metrics({k: float(v) for k, v in scores.items() if pd.notna(v)})
        rows.append({"threshold_pct": run["threshold_pct"], "train_on": run["train_on"], "split": label,
                     "model": run["model"], "features": run["features"], "params": str(run["params"]), **scores})
        print(f"[{i}/{len(runs)}] >={run['threshold_pct']}% {run['train_on']:6s} {label[:24]:24s} "
              f"{run['model']:12s} {run['features']:30s} onset PR-AUC {scores['onset_pr_auc']:.3f} "
              f"({scores['onset_pr_auc_lift']:.1f}x) · all {scores['pr_auc']:.3f}  {scores['fit_seconds']:.0f}s",
              flush=True)

    RESULTS.mkdir(parents=True, exist_ok=True)
    results = pd.DataFrame(rows).assign(benchmark=name, git_commit=commit)
    results.round(5).to_csv(RESULTS / f"benchmark_{name}.csv", index=False)
    board = (f"# Leaderboard: {name}\n\n{config.get('description', '').strip()}\n"
             + leaderboard(results, config.get("rank_by", "onset_pr_auc")))
    (RESULTS / f"leaderboard_{name}.md").write_text(board + "\n")
    print(board)


if __name__ == "__main__":
    main()
