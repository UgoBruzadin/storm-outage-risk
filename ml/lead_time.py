"""How much skill is left when the model only sees weather from before the decision?

The reported model summarizes the weather DURING each 6-hour block it scores: an upper
bound, since nobody knows that weather in advance. Here the decision is made L hours
before the block starts, and every input must be known by then:

  weather   the same summaries (max gust, total rain, ...) over the 6 hours ending at the
            decision time, from the hourly HRRR table: what had already happened
  recent    outages in the last block that had fully ended by the decision time: the
            previous block when L = 0, the one before it when 0 < L <= 6 (slightly
            pessimistic: up to L hours of the previous block are known by then)
  place     unchanged

The label and the set of scored blocks (new outages, >= 5%) are the same for every lead,
so the rows are comparable: only the information changes. Observed weather before the
decision is a lower bound for a real forecast, which can also see a storm coming that
hasn't arrived yet; the reported model is the upper bound. A forecast-based model sits
between the two.

Usage: pixi run python -m ml.lead_time
Writes ml/results/lead_time_2025.csv.
"""
import duckdb
import numpy as np
import pandas as pd

from ml import data, models
from ml.metrics import score

THRESHOLD_PCT = 5
TRAIN_YEARS, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2025
LEADS = [0, 1, 2, 3, 6]                       # hours between the decision and the block's start
FEATURES = ["weather", "weather+place+recent"]
# at the block's start, the official forecasts are known too: everything a utility has at that moment
EXTRA = {"0 h before": ["weather+place+recent+warnings+outlook"]}
PARAMS = {"n_estimators": 800, "learning_rate": 0.03, "max_depth": 4, "min_child_weight": 20,
          "subsample": 0.8, "colsample_bytree": 0.8}      # the final model's settings (final_2025.yaml)

# the 6-hour summaries of int_study__weather_6h, over any 6 consecutive hours
WEATHER_SQL = """
    max(gust_ms)                                                   AS gust_max_ms,
    max(wind10_ms)                                                 AS wind10_max_ms,
    max(wind850_ms)                                                AS wind850_max_ms,
    max(sqrt((u500 - u10) ^ 2 + (v500 - v10) ^ 2))                 AS shear_0_6km_max_ms,
    max(cape_jkg)                                                  AS cape_max_jkg,
    sum(precip_mm)                                                 AS precip_sum_mm,
    max(precip_mm)                                                 AS precip_max_1h_mm,
    min(temp_c)                                                    AS temp_min_c,
    avg(temp_c)                                                    AS temp_mean_c,
    min(freezing_level_m)                                          AS freezing_level_min_m,
    count(*) FILTER (WHERE temp_c <= 0 AND precip_mm > 0)          AS icing_hours,
    count(*) FILTER (WHERE cape_jkg >= 500 AND precip_mm >= 2
                       AND freezing_level_m <= 3500)               AS hail_hours
"""
BASE_WEATHER = ["gust_max_ms", "wind10_max_ms", "wind850_max_ms", "shear_0_6km_max_ms", "cape_max_jkg",
                "precip_sum_mm", "precip_max_1h_mm", "temp_min_c", "temp_mean_c", "freezing_level_min_m",
                "icing_hours", "hail_hours"]


def weather_before(lead, years, db=data.DB):
    """Weather summaries over the 6 hours ending `lead` hours before each block starts.
    Hours [t - lead - 6, t - lead) are moved forward by lead + 6 hours, which lands them in
    the block starting at t; a block gets a row only if all 6 hours exist."""
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        WITH shifted AS (
            SELECT *, hour + to_hours({lead + 6}) AS target FROM staging.stg_hrrr__hourly
        )
        SELECT region_fips,
               date_trunc('day', target) + to_hours(6 * (hour(target) // 6)) AS block_start,
               {WEATHER_SQL}
        FROM shifted
        WHERE year(target) BETWEEN {min(years)} AND {max(years)}
        GROUP BY ALL
        HAVING count(*) = 6
    """).df()
    con.close()
    return df


def at_lead(df, lead):
    """The modeling table as known `lead` hours before each block: weather and recent outages replaced."""
    before = weather_before(lead, sorted(df["year"].unique()))
    out = df.drop(columns=BASE_WEATHER).merge(before, on=["region_fips", "block_start"], how="inner")
    if lead > 0:
        # the previous block hasn't ended yet: use the one before it, and the 24 hours before that
        out = out.sort_values(["region_fips", "block_start"])
        g = out.groupby("region_fips")
        prev_ok = g["block_start"].diff() == pd.Timedelta(hours=6)
        out["max_pct_out_prev_24h"] = g["max_pct_out_prev_24h"].shift(1).where(prev_ok)
        out["prev_block_pct_out"] = g["prev_block_pct_out"].shift(1).where(prev_ok)
    return data.add_derived(out.drop(columns=["year"]))


def main():
    df = data.load(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR])
    keys = df.loc[(df.year == TEST_YEAR) & df.is_onset, ["region_fips", "block_start"]]
    tables = {"during the block (reported model)": df} | {f"{lead} h before": at_lead(df, lead) for lead in LEADS}
    # score every lead on the same new-outage blocks: those every table has
    common = keys
    for t in tables.values():
        common = common.merge(t[["region_fips", "block_start"]], on=["region_fips", "block_start"])
    rows = []
    for name, table in tables.items():
        train = table[table.year.isin(TRAIN_YEARS)]
        test = table.merge(common, on=["region_fips", "block_start"])
        for spec in FEATURES + EXTRA.get(name, []):
            features = data.resolve_features(spec)
            model = models.build("xgboost", PARAMS).fit(train[features], train["y"])
            p = model.predict_proba(test[features])[:, 1]
            s = score(test["y"].to_numpy(), p)
            rows.append({"information": name, "features": spec, "onset_pr_auc": s["pr_auc"],
                         "lift_top1": s["precision_top1"] / test["y"].mean(), "caught_top1": s["recall_top1"],
                         "n_blocks": len(test), "n_events": int(test["y"].sum())})
            print(rows[-1])
    result = pd.DataFrame(rows)
    result.to_csv(data.ROOT / "ml" / "results" / "lead_time_2025.csv", index=False)
    with pd.option_context("display.width", 200):
        print(result.pivot_table(index="information", columns="features", values="onset_pr_auc")
                    .reindex(list(tables)).round(3))


if __name__ == "__main__":
    np.random.seed(0)
    main()
