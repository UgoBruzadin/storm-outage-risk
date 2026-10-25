"""Train the final model and export everything the dashboard reads.

The app never runs a model or touches the 11 GB warehouse — it reads these
small Parquet files (data/app/), locally or from Hugging Face once published.

The final model is trained on 2024 and predicts 2025: every prediction shown
in the app is for a year the model never saw.

Writes data/app/:
  regions.parquet      216 regions: name, GeoJSON shape (simplified), place + resilience metrics
  predictions.parquet  2025, every region x 6-hour block: predicted probability, actual outage, weather
  storms.parquet       the biggest 2025 outage blocks, for the storm-replay picker
  importance.parquet   permutation importance of the final model's features
  metrics.parquet      every evaluated run (from ml/results/)
  meta.json            what was trained, on what, and when

Usage: pixi run export-app [--features weather+place+history] [--threshold 5]
"""
import argparse
import json
from datetime import UTC, datetime

import duckdb
import geopandas as gpd
import pandas as pd
from sklearn.inspection import permutation_importance
from train import DB, FEATURE_SETS, RESULTS, ROOT, YEARS, load, make_model

OUT = ROOT / "data" / "app"
REGIONS_GEO = ROOT / "data" / "raw" / "geo" / "regions_mo_il.parquet"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default="weather+place+history", choices=list(FEATURE_SETS))
    parser.add_argument("--threshold", type=float, default=5.0)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    features = FEATURE_SETS[args.features]

    # --- final model: train on the first year, predict the second -------------
    df = load(args.threshold)
    train, test = df[df.year == YEARS[0]], df[df.year == YEARS[1]].copy()
    model = make_model("hgb").fit(train[features], train["y"])
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
    con = duckdb.connect(str(DB), read_only=True)
    info = con.sql("""
        SELECT r.*, s.hours_out_per_customer, s.events_per_year, s.storm_hit_rate,
               s.quiet_event_rate, s.median_event_hours, s.repeat_7d_share, s.history_start, s.history_end
        FROM intermediate.int_mo_il__regions AS r
        JOIN marts.mart_mo_il__region_resilience AS s USING (region_fips)
    """).df()
    con.close()
    geo = gpd.read_parquet(REGIONS_GEO)[["region_fips", "geometry"]]
    geo["geometry"] = geo.geometry.simplify(0.005, preserve_topology=True)   # ~500 m: plenty for a state map
    geo["geojson"] = [json.dumps(g.__geo_interface__) for g in geo.geometry]
    regions = info.merge(geo[["region_fips", "geojson"]], on="region_fips")
    regions.to_parquet(OUT / "regions.parquet", index=False)

    # --- metrics from every evaluation run ------------------------------------
    runs = [pd.read_csv(p).assign(threshold_pct=float(p.stem.split("ge")[1].rstrip("pct")))
            for p in sorted(RESULTS.glob("summary_ge*pct.csv"))]
    pd.concat(runs).to_parquet(OUT / "metrics.parquet", index=False)

    meta = {
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "features": args.features,
        "feature_list": features,
        "threshold_pct": args.threshold,
        "train_year": YEARS[0],
        "test_year": YEARS[1],
        "n_regions": int(df.region_fips.nunique()),
        "test_events": int(test["y"].sum()),
        "test_blocks": int(len(test)),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    sizes = {p.name: f"{p.stat().st_size / 1e6:.1f} MB" for p in sorted(OUT.iterdir())}
    print(json.dumps(meta, indent=2), "\n", sizes)


if __name__ == "__main__":
    main()
