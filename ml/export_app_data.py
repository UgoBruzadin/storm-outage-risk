"""Train the final model and export everything the dashboard reads.

The app never runs a model or touches the 11 GB warehouse — it reads these
small Parquet files (data/app/), locally or from Hugging Face once published.

Which model? The `final:` section of a benchmark config (default
ml/benchmarks/quick.yaml) — pick the winner of your benchmark there. It's
trained on the config's first year and predicts the last one, so every
prediction in the app is for a year the model never saw.

Writes data/app/:
  regions.parquet      216 regions: name, GeoJSON shape (simplified), place + resilience metrics
  predictions.parquet  test year, every region x 6-hour block: probability, actual outage, weather
  storms.parquet       the biggest test-year outage blocks, for the storm-replay picker
  importance.parquet   permutation importance of the final model's features
  metrics.parquet      every benchmark result in ml/results/benchmark_*.csv
  meta.json            what was trained, on what, and the app's alert level

Usage: pixi run export-app [--config ml/benchmarks/full.yaml]
"""
import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
import yaml
from sklearn.inspection import permutation_importance

from ml import data, models

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "app"
RESULTS = ROOT / "ml" / "results"
REGIONS_GEO = ROOT / "data" / "raw" / "geo" / "regions_study.parquet"


def benchmark_thresholds(config):
    value = config["data"]["threshold_pct"]
    return value if isinstance(value, list) else [value]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "ml" / "benchmarks" / "quick.yaml")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    final, years = config["final"], config["data"]["years"]
    features = data.resolve_features(final["features"])
    OUT.mkdir(parents=True, exist_ok=True)

    # --- final model: train on the first year, predict the last ---------------
    threshold = final.get("threshold_pct", benchmark_thresholds(config)[0])
    df = data.load(threshold, years)
    train, test = df[df.year == min(years)], df[df.year == max(years)].copy()
    model = models.build(final["model"], final.get("params")).fit(train[features], train["y"])
    test["prob"] = model.predict_proba(test[features])[:, 1]

    keep = ["region_fips", "block_start", "prob", "y", "peak_out", "peak_pct_out",
            "gust_max_ms", "cape_max_jkg", "precip_sum_mm", "shear_0_6km_max_ms",
            "storm_reports", "storm_max_wind_kt", "storm_tornado"]
    test[keep].to_parquet(OUT / "predictions.parquet", index=False)

    # --- storms: blocks where the most customers lost power ------------------
    storms = (test.groupby("block_start")
                  .agg(customers_out=("peak_out", "sum"), regions_hit=("y", "sum"),
                       mean_prob=("prob", "mean"), reports=("storm_reports", "sum"))
                  .reset_index().sort_values("customers_out", ascending=False).head(40))
    storms.to_parquet(OUT / "storms.parquet", index=False)

    # --- importance: how much the score drops when a feature is shuffled -----
    sample = test.sample(min(40_000, len(test)), random_state=0)
    imp = permutation_importance(model, sample[features], sample["y"], scoring="average_precision",
                                 n_repeats=3, random_state=0)
    (pd.DataFrame({"feature": features, "importance": imp.importances_mean, "std": imp.importances_std})
       .sort_values("importance", ascending=False)
       .to_parquet(OUT / "importance.parquet", index=False))

    # --- regions: shapes + everything known about each place ------------------
    con = duckdb.connect(str(data.DB), read_only=True)
    info = con.sql("""
        SELECT r.*, s.hours_out_per_customer, s.events_per_year, s.storm_hit_rate,
               s.quiet_event_rate, s.median_event_hours, s.repeat_7d_share, s.history_start, s.history_end
        FROM intermediate.int_study__regions AS r
        JOIN marts.mart_study__region_resilience AS s USING (region_fips)
    """).df()
    con.close()
    geo = gpd.read_parquet(REGIONS_GEO)[["region_fips", "geometry"]]
    geo["geometry"] = geo.geometry.simplify(0.005, preserve_topology=True)   # ~500 m: plenty for a state map
    geo["geojson"] = [json.dumps(g.__geo_interface__) for g in geo.geometry]
    info.merge(geo[["region_fips", "geojson"]], on="region_fips").to_parquet(OUT / "regions.parquet", index=False)

    # --- every benchmark result -------------------------------------------------
    benchmarks = [pd.read_csv(p) for p in sorted(RESULTS.glob("benchmark_*.csv"))]
    if benchmarks:
        results = pd.concat(benchmarks, ignore_index=True)
        results["split_kind"] = results["split"].str.split("(").str[0]
        results.to_parquet(OUT / "metrics.parquet", index=False)

    # Alert level for the app: the top 1% of predicted risk. A fixed 0.5 would almost never
    # fire — events are rare (~1% of blocks), so probabilities stay low even before big storms.
    alert = float(test["prob"].quantile(0.99))
    alerts = test["prob"] >= alert
    meta = {
        "alert_threshold": round(alert, 4),
        "alert_precision": round(float(test.loc[alerts, "y"].mean()), 4),
        "alert_recall": round(float(alerts[test["y"] == 1].mean()), 4),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": str(args.config.relative_to(ROOT)) if args.config.is_absolute() else str(args.config),
        "model": final["model"],
        "params": final.get("params", {}),
        "features": final["features"],
        "feature_list": features,
        "threshold_pct": threshold,
        "train_year": min(years),
        "test_year": max(years),
        "n_regions": int(df.region_fips.nunique()),
        "test_events": int(test["y"].sum()),
        "test_blocks": int(len(test)),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    sizes = {p.name: f"{p.stat().st_size / 1e6:.1f} MB" for p in sorted(OUT.iterdir())}
    print(json.dumps({k: v for k, v in meta.items() if k != "feature_list"}, indent=2), "\n", sizes)


if __name__ == "__main__":
    main()
