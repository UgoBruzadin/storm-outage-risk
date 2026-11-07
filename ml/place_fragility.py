"""Which counties lose power more often than their weather explains, and is it the lines? (2020-2025)

Per county: new outages (O) against what a weather-only model expects (E). The model is cross-fitted over 5 county
folds, so a county's expectation never uses its own outages; quiet hours are subsampled 1 in 10 for training and
weighted back. log((O + 1) / (E + 1)) is then adjusted for county size (log customers, log housing density): a big
county rarely reaches 5% out, which is arithmetic, not fragility. The size fit uses well-tracked counties only.

Tracked: someone out in at least 5% of hours. Below that EAGLE-I barely covers the county, so its counts say little.

Usage: pixi run python -m ml.place_fragility
Writes ml/results/place_fragility.csv and prints how much line exposure (ingest/fetch_roads.py) explains.
"""
import duckdb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict
from xgboost import XGBClassifier

from ml import data
from ml.moving_window import onset_hours

YEARS = range(2020, 2026)
TRACKED_SHARE = 0.05
WEATHER = ["gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms", "cape_max_jkg", "precip_sum_mm",
           "precip_max_1h_mm", "temp_min_c", "temp_mean_c", "freezing_level_min_m", "icing_hours", "hail_hours",
           "precip_prev_72h_mm", "month", "hour_utc"]
ROADS = data.ROOT / "data" / "raw" / "place" / "roads.csv"
UTILITIES = data.ROOT / "data" / "raw" / "place" / "utilities.csv"
OUT = data.ROOT / "ml" / "results" / "place_fragility.csv"


def observed_expected():
    con = duckdb.connect(str(data.DB), read_only=True)
    h = con.sql(f"""SELECT region_fips, hour, {", ".join(WEATHER)} FROM marts.mart_study__region_1h
                    WHERE has_weather AND pct_out IS NOT NULL
                      AND year(hour) BETWEEN {min(YEARS)} AND {max(YEARS)}""").df()
    cov = con.sql(f"""SELECT region_fips, avg(typical_share) AS any_out_share FROM marts.mart_study__region_coverage
                      WHERE year BETWEEN {min(YEARS)} AND {max(YEARS)} GROUP BY 1""").df()
    size = con.sql("""SELECT region_fips, customers, housing_per_km2 FROM marts.mart_study__region_resilience""").df()
    con.close()
    onsets = pd.concat([onset_hours(y) for y in YEARS])
    keys = pd.MultiIndex.from_frame(onsets[["region_fips", "hour"]])
    h["y"] = pd.MultiIndex.from_frame(h[["region_fips", "hour"]]).isin(keys).astype(int)
    rng = np.random.default_rng(0)
    regions = sorted(h.region_fips.unique(), key=lambda f: f[::-1])
    fold = h.region_fips.map({r: i % 5 for i, r in enumerate(regions)})
    h["p"] = 0.0
    for k in range(5):
        tr = h[(fold != k) & ((h.y == 1) | (rng.random(len(h)) < 0.1))]
        m = XGBClassifier(n_estimators=400, learning_rate=0.05, max_depth=4, min_child_weight=20, subsample=0.8,
                          colsample_bytree=0.8, n_jobs=8, random_state=0)
        m.fit(tr[WEATHER], tr.y, sample_weight=np.where(tr.y == 1, 1.0, 10.0))
        h.loc[fold == k, "p"] = m.predict_proba(h.loc[fold == k, WEATHER])[:, 1]
        print("fold", k, flush=True)
    g = h.groupby("region_fips").agg(new_outages=("y", "sum"), expected=("p", "sum")).reset_index()
    return g.merge(cov, on="region_fips").merge(size, on="region_fips")


def main():
    d = observed_expected()
    d["tracked"] = d.any_out_share >= TRACKED_SHARE
    d["log_ratio"] = np.log((d.new_outages + 1) / (d.expected + 1))
    size = np.column_stack([np.log(d.customers), np.log(d.housing_per_km2)])
    fit = LinearRegression().fit(size[d.tracked], d.log_ratio[d.tracked])
    d["log_ratio_after_size"] = d.log_ratio - fit.predict(size)
    d["ratio"] = np.exp(d.log_ratio)
    d["ratio_after_size"] = np.exp(d.log_ratio_after_size)
    d.round(4).to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(d)} counties, {int((~d.tracked).sum())} barely tracked")

    # how much do line exposure and trees along the lines explain, against size alone? (tracked counties)
    t = d[d.tracked].merge(pd.read_csv(ROADS, dtype={"region_fips": str}), on="region_fips")
    t = t.merge(pd.read_csv(UTILITIES, dtype={"region_fips": str})[["region_fips", "util_share_coop"]],
                on="region_fips", how="left")
    t["log_customers"], t["log_density"] = np.log(t.customers), np.log(t.housing_per_km2)
    t["log_road_per_customer"] = np.log(t.road_km / t.customers)

    def cv_r2(cols):
        scores = []
        for seed in range(20):
            p = cross_val_predict(LinearRegression(), t[cols], t.log_ratio, cv=KFold(10, shuffle=True,
                                                                                      random_state=seed))
            scores.append(1 - ((t.log_ratio - p) ** 2).sum() / ((t.log_ratio - t.log_ratio.mean()) ** 2).sum())
        return np.mean(scores)

    def partial(col, controls):
        x = np.column_stack([np.ones(len(t))] + [t[c] for c in controls])
        res = lambda v: v - x @ np.linalg.lstsq(x, v, rcond=None)[0]  # noqa: E731
        return stats.spearmanr(res(t[col]), res(t.log_ratio))[0]

    size_cols = ["log_customers", "log_density"]
    lines = size_cols + ["log_road_per_customer", "road_treed_share"]
    print(f"\n{len(t)} tracked counties, cross-validated R^2 for log(O/E):")
    for name, cols in {"size": size_cols, "road per customer": ["log_road_per_customer"],
                       "size + road per customer": size_cols + ["log_road_per_customer"],
                       "size + road per customer + treed road share": lines,
                       "... + co-op share": lines + ["util_share_coop"]}.items():
        print(f"  {name:45s} {cv_r2(cols):.3f}")
    for col in ("util_share_coop", "canopy_dense_share"):
        if col not in t:
            t = t.merge(pd.read_csv(data.ROOT / "data" / "raw" / "geo" / "tree_canopy_2021.csv",
                                    dtype={"region_fips": str})[["region_fips", col]], on="region_fips")
        print(f"  {col}: partial r after size {partial(col, size_cols):+.2f}, after size + lines "
              f"{partial(col, lines):+.2f}")


if __name__ == "__main__":
    main()
