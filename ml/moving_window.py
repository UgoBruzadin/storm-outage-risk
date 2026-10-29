"""The moving-window benchmark: a decision every hour, about the 6 hours starting L hours later.

Every input is known at the decision time (marts.mart_study__region_1h): the weather of the
6 hours before it, outages up to the hour before, NWS warnings in force and the latest SPC
outlook, and the place. Scored on new outages only (the region was below 5% when the window
began), trained on 2020–2024, tested on 2025, for leads of 0, 1, 2, 3 and 6 hours.

Per lead and model:
  onset_pr_auc      over every scored decision hour (rows overlap: one outage sits in up
                    to 6 consecutive windows, so this is a ranking score, not a count)
  caught            share of 2025's new outages (hours a region crossed 5% from below) that
                    an alert flagged in time: some decision hour h with the outage hour inside
                    [h + L, h + L + 6) had probability >= the alert level
  alert_episodes    runs of consecutive alerted hours in one region: roughly, crew call-outs
  alert level       the top 1% of the same model trained on 2020–2023 and scored on 2024,
                    fixed before 2025 is scored

Usage: pixi run python -m ml.moving_window [--leads 0,2]
Writes ml/results/moving_window_2025.csv.
"""
import argparse

import pandas as pd

from ml import data, models
from ml.metrics import score

THRESHOLD_PCT = 5
TRAIN_YEARS, VAL_YEAR, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2024, 2025
PARAMS = {"n_estimators": 800, "learning_rate": 0.03, "max_depth": 4, "min_child_weight": 20,
          "subsample": 0.8, "colsample_bytree": 0.8}      # the 6-hour final model's settings
RUNS = [  # (label, model, feature spec)
    ("Warnings + outlook (rate table)", "official", None),
    ("Model: weather + place + recent", "xgboost", "weather+place+recent_now"),
    ("+ warnings + outlook", "xgboost", "weather+place+recent_now+warnings+outlook"),
    ("+ time since last outage", "xgboost", "weather+place+recent_now+warnings+outlook+since"),
]


def onset_hours(year, db=data.DB):
    """Every hour a region crossed THRESHOLD_PCT from below (the hour before known and under it)."""
    import duckdb
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        SELECT region_fips, hour FROM (
            SELECT region_fips, hour, pct_out, lag(pct_out) OVER (PARTITION BY region_fips ORDER BY hour) AS before
            FROM marts.mart_study__region_1h WHERE year(hour) BETWEEN {year - 1} AND {year})
        WHERE year(hour) = {year} AND pct_out >= {THRESHOLD_PCT} AND before < {THRESHOLD_PCT}
    """).df()
    con.close()
    return df


def fit_predict(model, spec, train, test):
    cols = models.NEEDS_COLUMNS.get(model) if spec is None else data.resolve_features(spec)
    fitted = models.build(model, None if spec is None else PARAMS).fit(train[cols], train["y"])
    return fitted.predict_proba(test[cols])[:, 1]


def caught(test, flagged, onsets, lead):
    """Share of onset hours inside the window of at least one flagged decision hour."""
    alerts = test.loc[flagged, ["region_fips", "block_start"]]
    hits = set()
    for offset in range(lead, lead + 6):                  # the outage hour = decision hour + offset
        hits |= set(zip(alerts.region_fips, alerts.block_start + pd.Timedelta(hours=offset), strict=True))
    return sum((r, h) in hits for r, h in zip(onsets.region_fips, onsets.hour, strict=True)) / len(onsets)


def episodes(test, flagged):
    a = test.loc[flagged, ["region_fips", "block_start"]].sort_values(["region_fips", "block_start"])
    new = (a.groupby("region_fips").block_start.diff() != pd.Timedelta(hours=1))
    return int(new.sum())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leads", default=",".join(map(str, data.HOURLY_LEADS)))
    leads = [int(x) for x in parser.parse_args().leads.split(",")]
    onsets = onset_hours(TEST_YEAR)
    rows = []
    for lead in leads:
        df = data.load_hourly(THRESHOLD_PCT, TRAIN_YEARS + [TEST_YEAR], lead)
        train, test = df[df.year.isin(TRAIN_YEARS)], df[df.year == TEST_YEAR]
        val_train, val = df[df.year < VAL_YEAR], df[df.year == VAL_YEAR]
        for label, model, spec in RUNS:
            p = fit_predict(model, spec, train, test)
            level = pd.Series(fit_predict(model, spec, val_train, val)).quantile(0.99)
            flagged = pd.Series(p >= level, index=test.index)
            s = score(test["y"].to_numpy(), p)
            rows.append({"lead_hours": lead, "run": label, "onset_pr_auc": s["pr_auc"],
                         "event_rate": test["y"].mean(), "alert_level": level, "alert_share": flagged.mean(),
                         "alert_precision": test.loc[flagged, "y"].mean(),
                         "caught": caught(test, flagged, onsets, lead),
                         "alert_episodes": episodes(test, flagged), "n_rows": len(test), "n_onsets": len(onsets)})
            print({k: round(v, 4) if isinstance(v, float) else v for k, v in rows[-1].items()}, flush=True)
        out = pd.DataFrame(rows)
        out.to_csv(data.ROOT / "ml" / "results" / "moving_window_2025.csv", index=False)
    print(out.pivot(index="run", columns="lead_hours", values="onset_pr_auc").round(3))
    print(out.pivot(index="run", columns="lead_hours", values="caught").round(3))


if __name__ == "__main__":
    main()
