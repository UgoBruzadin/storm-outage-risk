"""The benchmark machinery: if a split leaks or a metric is wrong, every comparison is wrong.

Uses a small synthetic frame with every feature column, so no warehouse is needed (the loader test
builds a tiny DuckDB file of its own).
"""
import importlib.util

import duckdb
import numpy as np
import pandas as pd
import pytest

from ml import benchmark, data, models, splits
from ml.metrics import score


@pytest.fixture(scope="module")
def frame():
    """2 years x 10 regions x 40 blocks, every feature column, ~10% events driven by gusts."""
    rng = np.random.default_rng(0)
    rows = []
    for year in (2024, 2025):
        for r in range(10):
            for b in range(40):
                rows.append({"region_fips": f"29{r:03d}", "block_start": pd.Timestamp(f"{year}-03-01")
                             + pd.Timedelta(hours=6 * b), "customers": 10_000 + 1_000 * r})
    df = pd.DataFrame(rows)
    every = {c for group in data.FEATURE_GROUPS.values() for c in group}
    for col in every - {"log_customers", "wind_x_precip", "wind_squared", "shear_x_cape", "month", "block_hour_utc"}:
        df[col] = rng.normal(size=len(df))
    df["month"] = df["block_start"].dt.month
    df["block_hour_utc"] = df["block_start"].dt.hour
    df["peak_pct_out"] = np.where(df["gust_max_ms"] > 1.3, 8.0, 0.5)
    return data.label(data.add_derived(df), threshold_pct=5)


def test_feature_arithmetic():
    with_canopy = data.resolve_features("weather+place")
    without = data.resolve_features("weather+place-canopy")
    assert set(with_canopy) - set(without) == set(data.FEATURE_GROUPS["canopy"])
    assert len(with_canopy) == len(set(with_canopy))                    # no duplicates
    assert data.resolve_features("weather") == data.FEATURE_GROUPS["weather"]


def test_time_split_trains_on_the_past(frame):
    [(_, tr, te)] = list(splits.make_splits(frame, "time", train_years=[2024], test_years=[2025]))
    assert frame.iloc[tr].year.max() < frame.iloc[te].year.min()
    with pytest.raises(AssertionError):
        list(splits.make_splits(frame, "time", train_years=[2025], test_years=[2024]))


def test_county_split_never_shares_a_region(frame):
    tested = []
    for _, tr, te in splits.make_splits(frame, "county", folds=5):
        assert not set(frame.iloc[tr].region_fips) & set(frame.iloc[te].region_fips)
        tested += list(te)
    assert sorted(tested) == list(range(len(frame)))                   # every row tested exactly once


def test_random_split_tests_every_row_once(frame):
    tested = np.concatenate([te for _, _, te in splits.make_splits(frame, "random", folds=5)])
    assert sorted(tested) == list(range(len(frame)))


def test_metrics_on_known_answers():
    y = np.array([0] * 98 + [1, 1])
    perfect = score(y, y * 0.9 + 0.05)
    assert perfect["pr_auc"] == pytest.approx(1.0) and perfect["roc_auc"] == pytest.approx(1.0)
    assert perfect["precision_top1"] == 1.0 and perfect["pr_auc_lift"] == pytest.approx(50)
    flat = score(y, np.full(100, 0.02))
    assert flat["pr_auc"] == pytest.approx(0.02)                        # no skill = the event rate


@pytest.mark.parametrize("name", sorted(models.REGISTRY))
def test_every_model_fits_and_predicts(frame, name):
    if name in ("lightgbm", "xgboost") and importlib.util.find_spec(name) is None:
        pytest.skip(f"{name} not installed in this environment")
    cols = models.NEEDS_COLUMNS.get(name, []) if name in benchmark.BASELINES else data.resolve_features("weather")
    params = {"n_estimators": 20} if name in ("lightgbm", "xgboost", "random_forest") else {}
    model = models.build(name, params).fit(frame[cols], frame["y"])
    p = model.predict_proba(frame[cols])[:, 1]
    assert p.shape == (len(frame),) and np.all((p >= 0) & (p <= 1))


def test_plan_and_grid():
    config = {"data": {"threshold_pct": 5}, "splits": [{"kind": "time"}, {"kind": "county"}],
              "features": ["weather", "weather+place"],
              "models": [{"name": "prior"}, {"name": "hgb", "params": {"max_iter": [50, 100], "learning_rate": 0.1}}]}
    runs = benchmark.plan(config)
    # per split: 1 baseline (no feature sets) + 2 feature sets x 2 grid points
    assert len(runs) == 2 * (1 + 2 * 2)
    assert benchmark.expand_grid({"a": [1, 2], "b": 3}) == [{"a": 1, "b": 3}, {"a": 2, "b": 3}]


def test_evaluate_learns_the_signal(frame):
    run = {"split": {"kind": "time", "train_years": [2024], "test_years": [2025]},
           "model": "hgb", "features": "weather", "params": {"max_iter": 50}}
    scores = benchmark.evaluate(frame, run)
    assert scores["pr_auc"] > 3 * scores["event_rate"]                 # gusts drive the label


def test_plan_sweeps_thresholds_and_training_rows():
    config = {"data": {"threshold_pct": [1, 5, 10], "train_on": ["all", "onsets"]},
              "splits": [{"kind": "time"}], "features": ["weather"], "models": [{"name": "hgb"}]}
    runs = benchmark.plan(config)
    assert len(runs) == 3 * 2
    expected = {(t, o) for t in (1, 5, 10) for o in ("all", "onsets")}
    assert {(r["threshold_pct"], r["train_on"]) for r in runs} == expected


def test_onsets_exclude_ongoing_and_unknown_blocks():
    df = pd.DataFrame({"peak_pct_out": [0.0, 6.0, 7.0, 0.0, 6.0],
                       "prev_block_pct_out": [np.nan, 0.0, 6.0, 7.0, 0.5]})
    labeled = data.label(df, threshold_pct=5)
    # unknown previous block -> not an onset; previous block already >= 5% -> not an onset
    assert labeled["is_onset"].tolist() == [False, True, False, False, True]
    assert labeled["y"].tolist() == [0, 1, 1, 0, 1]


def test_evaluate_reports_onset_scores(frame):
    run = {"threshold_pct": 5, "train_on": "onsets", "split": {"kind": "county", "folds": 3},
           "model": "hgb", "features": "weather", "params": {"max_iter": 30}}
    scores = benchmark.evaluate(frame, run)
    assert scores["onset_n_test"] == int(frame["is_onset"].sum())
    assert scores["n_test"] == len(frame)


def test_metrics_without_events_are_nan_not_errors():
    s = score(np.zeros(10), np.linspace(0, 1, 10))
    assert np.isnan(s["pr_auc"]) and s["n_events"] == 0


def test_top1_alerts_exactly_one_percent_even_with_ties():
    y = np.r_[np.zeros(990), np.ones(10)]
    s = score(y, np.full(1000, 0.01))                  # a baseline: every block tied
    assert s["recall_top1"] < 1.0                      # was 1.0 when ties made every block an alert
    ranked = score(y, np.r_[np.zeros(990), np.ones(10)])
    assert ranked["precision_top1"] == 1.0 and ranked["recall_top1"] == 1.0   # top 10 of 1000 = the 10 events


def test_balanced_gives_events_and_non_events_equal_weight():
    class Recorder(models.RateBaseline):
        def fit(self, X, y, sample_weight=None):
            self.weight_ = sample_weight
            return super().fit(X, y)

    y = np.r_[np.zeros(90), np.ones(10)]
    fitted = models.Balanced(Recorder()).fit(pd.DataFrame({"x": np.arange(100)}), y)
    w = fitted.estimator_.weight_
    assert w[y == 1].sum() == pytest.approx(w[y == 0].sum())


def test_class_weight_balanced_reaches_a_pipeline(frame):
    model = models.build("logistic", {"class_weight": "balanced"})
    cols = data.resolve_features("weather")
    model.fit(frame[cols], frame["y"])                   # the weights must route to the last step
    assert model.predict_proba(frame[cols]).shape == (len(frame), 2)


@pytest.mark.parametrize("name", ["nws_warnings", "spc_outlook", "official"])
def test_official_baselines_run_without_features(frame, name):
    run = {"threshold_pct": 5, "split": {"kind": "time", "train_years": [2024], "test_years": [2025]},
           "model": name, "features": "-", "params": {}}
    assert 0 <= benchmark.evaluate(frame, run)["roc_auc"] <= 1


def test_f1_at_50():
    y = np.array([1, 1, 0, 0])
    s = score(y, np.array([0.9, 0.2, 0.7, 0.1]))        # flags 2 blocks, 1 of them an event
    assert s["precision_at_50"] == 0.5 and s["recall_at_50"] == 0.5 and s["f1_at_50"] == 0.5


def test_history_must_end_before_each_rows_own_year(frame):
    features = data.resolve_features("weather+place+history")
    as_of = frame.assign(history_end=pd.to_datetime(frame["year"].astype(str) + "-01-01"))
    data.check_history(as_of, features)                                 # as-of history: fine
    fixed = frame.assign(history_end=pd.Timestamp("2025-01-01"))        # covers 2024, a row year here
    with pytest.raises(ValueError, match="history"):
        data.check_history(fixed, features)
    data.check_history(fixed, data.resolve_features("weather+place"))   # no history features: fine


def test_seed_can_be_set_from_the_config():
    assert models.build("xgboost", {"random_state": 3}).get_params()["random_state"] == 3
    assert models.build("xgboost", {}).get_params()["random_state"] == 0


def test_load_reads_only_the_years_asked_for(tmp_path):
    """[2020, 2022] must not bring in 2021; recent-outage features still see the block before."""
    db = tmp_path / "w.duckdb"
    con = duckdb.connect(str(db))
    con.sql("CREATE SCHEMA marts")
    con.sql("""
        CREATE TABLE marts.mart_study__region_6h AS
        SELECT '29001' AS region_fips, t AS block_start, 1.0 * (year(t) - 2019) AS peak_pct_out, true AS has_weather,
               1000 AS customers, 10.0 AS gust_max_ms, 1.0 AS precip_sum_mm, 5.0 AS shear_0_6km_max_ms,
               100.0 AS cape_max_jkg, 8.0 AS wind10_max_ms, 0.0 AS precip_prev_72h_mm
        FROM range(TIMESTAMP '2020-12-31 18:00', TIMESTAMP '2022-01-01 06:00', INTERVAL 6 HOUR) AS r(t)
    """)
    con.sql("""
        CREATE TABLE marts.mart_study__region_history_asof (region_fips VARCHAR, as_of_year INT,
            hours_out_per_customer DOUBLE, events_per_year DOUBLE, storm_hit_rate DOUBLE, quiet_event_rate DOUBLE,
            repeat_7d_share DOUBLE, history_end TIMESTAMP)
    """)
    con.close()
    df = data.load(5, [2020, 2022], db=db)
    assert set(df["year"]) == {2020, 2022}
    first_2022 = df[df["block_start"] == pd.Timestamp("2022-01-01")].iloc[0]
    assert first_2022["prev_block_pct_out"] == 2.0          # the last 2021 block, outside the years asked for


def _hourly_warehouse(path, regions=("29001", "29003", "17001"), start="2023-12-31", end="2025-01-02"):
    """A tiny moving-window warehouse: mart_study__region_1h, coverage and neighbour pairs, ~3% outages."""
    con = duckdb.connect(str(path))
    for schema in ("marts", "intermediate"):
        con.sql(f"CREATE SCHEMA {schema}")
    leads = ", ".join(f"fut AS fut_max_pct_{x}, 0.0 AS start_pct_{x}" for x in data.HOURLY_LEADS)
    con.sql(f"""
        CREATE TABLE marts.mart_study__region_1h AS
        SELECT *, {leads} FROM (
            SELECT r AS region_fips, t AS hour, hour(t) AS hour_utc, true AS has_weather, 1000 AS customers,
                   0.0 AS pct_out, 0.0 AS pct_out_now, (hash(r || t::VARCHAR) % 100)::DOUBLE / 10 AS gust_max_ms,
                   1.0 AS precip_sum_mm, 5.0 AS shear_0_6km_max_ms, 100.0 AS cape_max_jkg, 8.0 AS wind10_max_ms,
                   0.0 AS precip_prev_72h_mm, (hash(t::VARCHAR || r) % 100 < 3) AS warn_svr, false AS warn_tor,
                   false AS warn_wind, false AS warn_winter, 1.0 AS spc_cat,
                   CASE WHEN hash(r || '|' || t::VARCHAR) % 100 < 3 THEN 9.0 ELSE 0.0 END AS fut
            FROM (SELECT unnest({list(regions)}) AS r),
                 range(TIMESTAMP '{start}', TIMESTAMP '{end}', INTERVAL 1 HOUR) AS g(t))
    """)
    con.sql("""CREATE TABLE marts.mart_study__region_coverage AS
               SELECT DISTINCT region_fips, year(hour) AS year, true AS tracked FROM marts.mart_study__region_1h""")
    con.sql(f"""CREATE TABLE intermediate.int_study__region_neighbors AS
                SELECT a.r AS region_fips, b.r AS neighbor_fips, true AS is_near, a.r < b.r AS is_upwind
                FROM (SELECT unnest({list(regions)}) AS r) a, (SELECT unnest({list(regions)}) AS r) b
                WHERE a.r <> b.r""")
    con.close()
    return path


def test_sampling_keeps_every_outage_and_weights_add_up(tmp_path):
    db = _hourly_warehouse(tmp_path / "w.duckdb")
    full = data.load_hourly(5, [2024], 2, neighbors=False, db=db)
    lean = data.load_hourly(5, [2024], 2, neighbors=False, db=db, neg_frac=0.1)
    assert lean.y.sum() == full.y.sum() and (lean[lean.y == 1].weight == 1).all()      # every outage, weight 1
    assert lean.weight.sum() == pytest.approx(len(full), rel=0.1)                       # stands for the full table
    assert len(lean) < 0.2 * len(full)
    again = data.load_hourly(5, [2024], 2, neighbors=False, db=db, neg_frac=0.1)
    assert lean[["region_fips", "block_start"]].equals(again[["region_fips", "block_start"]])   # same rows every run
    kept = set(zip(lean.region_fips, lean.block_start, strict=True))
    assert kept <= set(zip(full.region_fips, full.block_start, strict=True))
    both = data.load_hourly(5, [2024], 2, neighbors=False, db=db, neg_frac=0.1, sample_years=[])
    assert len(both) == len(full) and (both.weight == 1).all()                         # a scored year: never sampled


def test_hourly_counts_fit_the_same_rate_table_as_the_rows(tmp_path):
    db = _hourly_warehouse(tmp_path / "w.duckdb")
    rows = data.load_hourly(5, [2024], 2, neighbors=False, db=db)
    official = models.NEEDS_COLUMNS["official"]
    counts = data.hourly_counts(5, [2024], 2, official, db=db)
    assert counts.weight.sum() == len(rows)
    from_rows = models.build("official").fit(rows[official], rows.y)
    from_counts = models.build("official").fit(counts[official], counts.y, sample_weight=counts.weight)
    assert np.allclose(from_rows.predict_proba(rows[official]), from_counts.predict_proba(rows[official]))


def test_weighted_rate_table_equals_repeated_rows():
    X = pd.DataFrame({"g": [0, 0, 1, 1]})
    weighted = models.RateBaseline(by=("g",)).fit(X, [1, 0, 1, 0], sample_weight=[1, 3, 2, 2])
    expanded = pd.DataFrame({"g": [0, 0, 0, 0, 1, 1, 1, 1]})
    repeated = models.RateBaseline(by=("g",)).fit(expanded, [1, 0, 0, 0, 1, 1, 0, 0])
    assert np.allclose(weighted.predict_proba(X), repeated.predict_proba(X))
    assert weighted.overall_ == pytest.approx(repeated.overall_)


def test_neighbour_cache_by_year_matches_one_pass_and_rebuilds(tmp_path):
    db = _hourly_warehouse(tmp_path / "w.duckdb")
    cache = tmp_path / "nb"
    by_year = data.neighbor_features(db=db, cache=cache)
    folder = data._neighbor_cache_dir(db, cache)
    assert sorted(p.stem for p in folder.glob("*.parquet")) == ["2023", "2024", "2025"]
    con = duckdb.connect(str(db), read_only=True)
    base = con.sql("SELECT region_fips, hour, gust_max_ms FROM marts.mart_study__region_1h").df()
    con.close()
    # one pass by hand: the strongest gust among each region's near neighbours, every hour
    grid = base.pivot(index="hour", columns="region_fips", values="gust_max_ms")
    expect = pd.DataFrame({r: grid.drop(columns=r).max(axis=1) for r in grid.columns}).stack()
    expect = expect.rename("want").rename_axis(["hour", "region_fips"]).reset_index()
    got = by_year.merge(expect, on=["region_fips", "hour"])
    assert len(got) == len(base) and np.allclose(got.near_gust_max_ms, got.want)
    only = data.neighbor_features(db=db, cache=cache, years=[2024], states=["17"])
    assert set(only.region_fips) == {"17001"} and set(only.hour.dt.year) == {2024}
    import os
    os.utime(db, (1, 1))                                       # the warehouse "changed": the cache is rebuilt
    assert not data._neighbor_cache_valid(folder, db)
    data.neighbor_features(db=db, cache=cache, years=[2024])
    assert data._neighbor_cache_valid(folder, db)


def test_fast_bootstrap_equals_the_direct_one():
    from ml.uncertainty import day_weights, pr_auc_resamples, pr_auc_resamples_slow
    rng = np.random.default_rng(2)
    p = rng.random(20_000).round(3)                    # many ties
    y = (rng.random(20_000) < p * 0.05).astype(int)
    days = rng.integers(0, 40, 20_000)
    counts, _ = day_weights(np.arange(40), n=30)
    slow = pr_auc_resamples_slow(y, p, days, counts)
    assert np.allclose(pr_auc_resamples(y, p, days, counts), slow, rtol=1e-12, atol=0)
    assert np.allclose(pr_auc_resamples(y, p, days, counts, block=7), slow, rtol=1e-12, atol=0)   # across blocks


def test_cache_returns_the_same_table_and_follows_the_warehouse(tmp_path):
    db = _hourly_warehouse(tmp_path / "w.duckdb")
    first = data.load_hourly(5, [2024], 2, neighbors=False, db=db)
    again = data.load_hourly(5, [2024], 2, neighbors=False, db=db)              # read back from the cache
    pd.testing.assert_frame_equal(first, again)
    files = list(data.TABLE_CACHE.glob("hourly/*.parquet"))
    import os
    os.utime(db, (1, 1))                                                        # a rebuilt warehouse
    data.load_hourly(5, [2024], 2, neighbors=False, db=db)
    assert len(list(data.TABLE_CACHE.glob("hourly/*.parquet"))) == len(files) + 1   # built again, not reused


def test_bootstrap_pr_auc_matches_sklearn_with_day_weights():
    from sklearn.metrics import average_precision_score

    from ml.uncertainty import day_weights, pr_auc_resamples, storm_day
    rng = np.random.default_rng(1)
    p = rng.random(5000).round(2)                      # ties on purpose
    y = (rng.random(5000) < p * 0.2).astype(int)
    hours = pd.Series(pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 24 * 60, 5000), unit="h"))
    days = storm_day(hours)
    counts, codes = day_weights(days, n=3)
    for c, got in zip(counts, pr_auc_resamples(y, p, codes, counts), strict=True):
        assert np.isclose(got, average_precision_score(y, p, sample_weight=c[codes]))
    assert (days.dt.hour == 0).all() and (hours - days >= pd.Timedelta(hours=12)).all()
