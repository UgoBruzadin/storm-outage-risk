"""Train and evaluate outage models on marts.mart_mo_il__region_6h.

Replicates the weathernext-outage-forecasting setup — one row per county per
6-hour block, multi-ingredient weather features, label = peak outage >= 5% of
customers — and then asks this project's question: does knowing the *place*
(tree canopy, housing age, density, size) help predict outages in counties
the model has never seen?

Every combination of feature set x split x model is one MLflow run. A
summary table is also written to ml/results/ (small, committed to git).

Splits — how the test rows are chosen:
  time    train on 2024, test on 2025: "can it predict next year?"
  county  5-fold, each fold holds out ~1/5 of regions entirely: "can it
          predict a place it never saw?" — the honest test for place features
  random  80/20 by region-day, the weathernext approach. Neighbouring counties
          on the same storm day land on both sides, so scores come out
          optimistic — kept here on purpose, to show by how much.

Usage:
  pixi run train                    # everything (label >= 5%)
  pixi run train --threshold 1      # label >= 1%
  pixi run mlflow-ui                # browse runs at http://127.0.0.1:5000
"""
import argparse
import hashlib
from pathlib import Path

import duckdb
import mlflow
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "warehouse.duckdb"
RESULTS = ROOT / "ml" / "results"
TRACKING_URI = f"sqlite:///{ROOT / 'data' / 'mlflow.db'}"
ARTIFACTS = (ROOT / "data" / "mlruns").as_uri()
YEARS = (2024, 2025)

# weathernext's ingredients, as close as HRRR via Open-Meteo allows
WEATHER = [
    "gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms",
    "cape_max_jkg", "precip_sum_mm", "precip_max_1h_mm", "temp_min_c",
    "temp_mean_c", "freezing_level_min_m", "icing_hours", "hail_hours",
    # weathernext's interaction terms
    "wind_x_precip", "wind_squared", "shear_x_cape",
    # calendar
    "month", "block_hour_utc",
]
PLACE = [
    "log_customers", "housing_per_km2", "share_homes_pre1960",
    "median_year_built", "canopy_mean_pct", "canopy_dense_share",
]
# the region's own track record, from mart_mo_il__region_resilience (2020–2023,
# before the train/test years — known in advance, so no leakage)
HISTORY = [
    "hist_hours_out_per_customer", "hist_events_per_year", "hist_storm_hit_rate",
    "hist_quiet_event_rate", "hist_repeat_7d_share",
]
FEATURE_SETS = {
    "weather": WEATHER,
    "weather+place": WEATHER + PLACE,
    "weather+place-canopy": WEATHER + [c for c in PLACE if not c.startswith("canopy")],
    "weather+place+history": WEATHER + PLACE + HISTORY,
}


def load(threshold):
    con = duckdb.connect(str(DB), read_only=True)
    df = con.sql(f"""
        SELECT
            m.*,
            r.hours_out_per_customer  AS hist_hours_out_per_customer,
            r.events_per_year         AS hist_events_per_year,
            r.storm_hit_rate          AS hist_storm_hit_rate,
            r.quiet_event_rate        AS hist_quiet_event_rate,
            r.repeat_7d_share         AS hist_repeat_7d_share,
            r.history_end
        FROM marts.mart_mo_il__region_6h AS m
        JOIN marts.mart_mo_il__region_resilience AS r USING (region_fips)
        WHERE m.has_weather
          AND m.peak_pct_out IS NOT NULL
          AND year(m.block_start) BETWEEN {YEARS[0]} AND {YEARS[1]}
    """).df()
    # history must end before the first year we train or test on
    assert (df["history_end"] <= pd.Timestamp(f"{YEARS[0]}-01-01")).all(), "history overlaps train/test years"
    con.close()
    df["y"] = (df["peak_pct_out"] >= threshold).astype(int)
    df["year"] = df["block_start"].dt.year
    df["log_customers"] = np.log10(df["customers"])
    df["wind_x_precip"] = df["gust_max_ms"] * df["precip_sum_mm"]
    df["wind_squared"] = df["gust_max_ms"] ** 2
    df["shear_x_cape"] = df["shear_0_6km_max_ms"] * df["cape_max_jkg"]
    return df


def make_model(name):
    if name == "logistic":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(max_iter=2000, class_weight="balanced"))
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
                                          l2_regularization=1.0, random_state=0)


def splits(df, kind):
    """Yield (train_index, test_index) pairs."""
    if kind == "time":
        yield np.where(df["year"] == YEARS[0])[0], np.where(df["year"] == YEARS[1])[0]
    elif kind == "county":
        yield from GroupKFold(n_splits=5).split(df, groups=df["region_fips"])
    elif kind == "random":
        key = df["region_fips"] + df["block_start"].dt.date.astype(str)
        bucket = key.map(lambda k: int(hashlib.md5(k.encode()).hexdigest(), 16) % 5)
        yield np.where(bucket != 0)[0], np.where(bucket == 0)[0]


def evaluate(df, features, split, model_name):
    """Out-of-sample probability for every test row (pooled across folds)."""
    proba = pd.Series(np.nan, index=df.index)
    for train_idx, test_idx in splits(df, split):
        model = make_model(model_name)
        model.fit(df.iloc[train_idx][features], df.iloc[train_idx]["y"])
        proba.iloc[test_idx] = model.predict_proba(df.iloc[test_idx][features])[:, 1]
    tested = proba.notna()
    y, p = df.loc[tested, "y"], proba[tested]
    return {
        "pr_auc": average_precision_score(y, p),
        "roc_auc": roc_auc_score(y, p),
        "brier": brier_score_loss(y, p),
        "event_rate": y.mean(),
        "n_test": int(tested.sum()),
        "n_events": int(y.sum()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=5.0, help="label: peak %% of customers out >= this")
    parser.add_argument("--models", default="hgb,logistic")
    parser.add_argument("--splits", default="time,county,random")
    args = parser.parse_args()

    df = load(args.threshold)
    print(f"{len(df):,} region-blocks, {df.region_fips.nunique()} regions, "
          f"{df.y.sum():,} events (>= {args.threshold}%), rate {df.y.mean():.2%}")

    mlflow.set_tracking_uri(TRACKING_URI)
    exp_name = f"outage-6h-ge{args.threshold:g}pct"
    if mlflow.get_experiment_by_name(exp_name) is None:
        mlflow.create_experiment(exp_name, artifact_location=ARTIFACTS)
    mlflow.set_experiment(exp_name)

    rows = []
    for split in args.splits.split(","):
        for model_name in args.models.split(","):
            for set_name, features in FEATURE_SETS.items():
                with mlflow.start_run(run_name=f"{split}/{model_name}/{set_name}"):
                    scores = evaluate(df, features, split, model_name)
                    mlflow.log_params({"split": split, "model": model_name, "features": set_name,
                                       "threshold_pct": args.threshold, "n_features": len(features),
                                       "n_regions": df.region_fips.nunique(), "years": f"{YEARS[0]}-{YEARS[1]}"})
                    mlflow.log_metrics(scores)
                rows.append({"split": split, "model": model_name, "features": set_name, **scores})
                print(f"{split:7s} {model_name:9s} {set_name:22s} PR-AUC {scores['pr_auc']:.3f}  "
                      f"ROC-AUC {scores['roc_auc']:.3f}  (event rate {scores['event_rate']:.3%})", flush=True)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"summary_ge{args.threshold:g}pct.csv"
    pd.DataFrame(rows).round(4).to_csv(out, index=False)
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
