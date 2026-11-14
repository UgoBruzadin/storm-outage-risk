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
                    fixed before 2025 is scored; an alert needs a probability strictly above
                    it, so a rate table that gives many hours the same value can't flag
                    more than 1% of them by a tie

Usage: pixi run python -m ml.moving_window [--leads 0,2]
Writes ml/results/moving_window_2025.csv.
"""
import argparse

import pandas as pd

from ml import data, models
from ml.metrics import score, weighted_quantile

THRESHOLD_PCT = 5
TRAIN_YEARS, VAL_YEAR, TEST_YEAR = [2020, 2021, 2022, 2023, 2024], 2024, 2025
PARAMS = {"n_estimators": 800, "learning_rate": 0.03, "max_depth": 4, "min_child_weight": 20,
          "subsample": 0.8, "colsample_bytree": 0.8}      # the 6-hour final model's settings
# the final features, chosen on the 2024 validation year over seeds (hourly_ablation.py): neighbours
# in (+2.8% at 2 h, +5.7% at 6 h, every seed); canopy kept; time since the last outage (mixed) and
# rain in the past 72 h (worse with every seed) left out; training from 2020 (adding 2018–2019: +0.5%)
FEATURES = "weather+place+recent_now+warnings+outlook+neighbors"
RUNS = [  # (label, model, feature spec)
    ("Warnings + outlook (rate table)", "official", None),
    ("Model: weather + place + recent", "xgboost", "weather+place+recent_now"),
    ("+ warnings + outlook", "xgboost", "weather+place+recent_now+warnings+outlook"),
    ("+ neighbours (final)", "xgboost", FEATURES),
]


def onset_hours(year, db=data.DB):
    """Every hour a region crossed THRESHOLD_PCT from below (the hour before known and under it) after
    data.FRESH_HOURS with no hour at or above it: a new outage, not one hovering around the line."""
    import duckdb
    con = duckdb.connect(str(db), read_only=True)
    df = con.sql(f"""
        SELECT region_fips, hour FROM (
            SELECT region_fips, hour, pct_out, lag(pct_out) OVER w AS before,
                   max(pct_out) OVER (w ROWS BETWEEN {data.FRESH_HOURS} PRECEDING AND 1 PRECEDING) AS recent
            FROM marts.mart_study__region_1h WHERE year(hour) BETWEEN {year - 1} AND {year}
            WINDOW w AS (PARTITION BY region_fips ORDER BY hour))
        WHERE year(hour) = {year} AND pct_out >= {THRESHOLD_PCT} AND before < {THRESHOLD_PCT}
          AND recent < {THRESHOLD_PCT}
    """).df()
    con.close()
    return df


def fit_predict(model, spec, train, test):
    cols = models.NEEDS_COLUMNS.get(model) if spec is None else data.resolve_features(spec)
    fitted = models.build(model, None if spec is None else PARAMS).fit(train[cols], train["y"])
    return fitted.predict_proba(test[cols])[:, 1]


def fit_runs(runs, lead, train_years=TRAIN_YEARS, val_year=VAL_YEAR, levels=True, threshold=THRESHOLD_PCT,
             transform=None):
    """Each run fitted on the sampled training table (rate tables on the full table's counts), and its alert level:
    the top 1% of the same run trained on the years before val_year and scored on val_year (weighted, since
    val_year's rows are a sample; None if levels=False). Returns {label: (fitted, columns, level)}.
    transform(rows, year) -> rows changes each training year's rows (as predict_states' transform)."""
    train = data.sampled_years(threshold, train_years, lead, add=transform)
    val_train, val = train[train.year < val_year], train[train.year == val_year]
    early_years = [y for y in train_years if y < val_year]
    out = {}
    for label, model, spec in runs:
        cols = models.NEEDS_COLUMNS.get(model) if spec is None else data.resolve_features(spec)
        params = None if spec is None else PARAMS
        if spec is None:          # a rate table: exact counts over the full table, not the sample
            c = data.hourly_counts(threshold, train_years, lead, cols)
            fitted = models.build(model, params).fit(c[cols], c.y, sample_weight=c.weight)
        else:
            fitted = models.build(model, params).fit(train[cols], train.y, sample_weight=train.weight)
        level = None
        if levels:
            if spec is None:
                e = data.hourly_counts(threshold, early_years, lead, cols)
                early = models.build(model, params).fit(e[cols], e.y, sample_weight=e.weight)
            else:
                early = models.build(model, params).fit(val_train[cols], val_train.y, sample_weight=val_train.weight)
            level = weighted_quantile(early.predict_proba(val[cols])[:, 1], val.weight, 0.99)
        out[label] = (fitted, cols, level)
        print(f"lead {lead}: fitted {label}", flush=True)
    return out


def predict_states(fitted, year, lead, keep=("region_fips", "block_start", "y"), threshold=THRESHOLD_PCT,
                   transform=None, **kwargs):
    """Every run's probabilities for every decision of `year`, scored a state at a time (never sampled).
    fitted: {label: (model, columns, level)}; a label may be any hashable (a tuple becomes a column name as is).
    transform(rows, year) -> rows changes each state's rows before scoring (e.g. weather an hour late)."""
    parts = []
    for _, rows in data.state_rows(threshold, year, lead, **kwargs):
        if transform is not None:
            rows = transform(rows, year)
        out = rows[list(keep)].copy()
        for label, (m, cols, _) in fitted.items():
            out[label] = m.predict_proba(rows[cols])[:, 1]
        parts.append(out)
        del rows
    return pd.concat(parts, ignore_index=True)


def caught_flags(test, flagged, onsets, lead):
    """For each onset hour: inside the window of at least one flagged decision hour?"""
    alerts = test.loc[flagged, ["region_fips", "block_start"]]
    hits = set()
    for offset in range(lead, lead + 6):                  # the outage hour = decision hour + offset
        hits |= set(zip(alerts.region_fips, alerts.block_start + pd.Timedelta(hours=offset), strict=True))
    return [(r, h) in hits for r, h in zip(onsets.region_fips, onsets.hour, strict=True)]


def caught(test, flagged, onsets, lead):
    """Share of onset hours inside the window of at least one flagged decision hour."""
    return sum(caught_flags(test, flagged, onsets, lead)) / len(onsets)


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
        fitted = fit_runs(RUNS, lead)
        test = predict_states(fitted, TEST_YEAR, lead)
        for label, _, _ in RUNS:
            p, level = test[label].to_numpy(), fitted[label][2]
            flagged = pd.Series(p > level, index=test.index)
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
