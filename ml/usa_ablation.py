"""Which settings and inputs make the best USA model? (docs/experiments.md, E55; plan fixed before any result)

Most of the project's feature and setting decisions were made on Missouri + Illinois (E6, E15, E16, E47), about 1/15
of the USA's new outages. This re-asks the most informative of them on all 48 states + DC, one change at a time
against the headline recipe (moving_window.FEATURES + window weather, XGBoost, 2 hours ahead, fresh new outages).

  baselines  is the model more than weather with thresholds? The current model against the strongest such rules:
             each county's own outage rate by forecast gust level (shrunk toward the national rate, CountyGustRate),
             the same with one national table, XGBoost on the weather inputs alone, and warnings + outlook
  size     the XGBoost settings, on the current inputs (E16 again): depth, minimum child weight, trees
  inputs   with the size stage's settings, each group added on its own:
             duration / spread      hours with gusts >= 15 and >= 20 m/s, mean and median gust, largest gust minus
                                    mean wind, over the window (+6% on MO + IL, ml/wind_inputs.py)
             roads + street canopy  road per customer, share of road under dense canopy, mean canopy over roads (E49)
             history                the county's record over the 3 years before (E6, dropped on MO + IL)
             location               latitude and longitude (the West scores lowest)
             E47 place groups       every group of ml/place_extra.py together (+7.9% on held-out counties, 1 seed)
             monotone gust          no new input: the chance may never fall as the gust rises
  combine  the size stage's settings with every input group kept, together; and, since more inputs may need a bigger
           model, the same with depth + 2 and with twice the trees, each against the combined model

Selection only: trained on 2020-2023 with the weather that actually happened (as the headline), scored on every
decision of 2024 with the window weather from the newest HRRR run (issued 2 hours before; it needs forecast hours
4-9, which every 2024 run has, so all of 2024 counts, unlike E47's five-run mean). 2025 is never scored here.

The rule, fixed before any result: a change is kept if the gain over its reference on 2024, from the mean of three
seeds' chances, has a 95% storm-day bootstrap range above zero, and at least 2 of the 3 seeds are better. Held-out
counties (5 folds, each scored by a model trained without them, seed 0) are reported beside it as a check, not a
gate. The size stage keeps the highest-scoring setting that passes the rule (the current one if none does).

Usage: pixi run -e gpu python -m ml.usa_ablation baselines | size | inputs | combine | report [--smoke]
  --smoke   two states, 5 trees, one seed, two folds, trained on 2023 only, written to data/cache/usa_ablation_smoke:
            runs every line of a stage in minutes
Writes ml/results/usa_ablation_2024.csv (every score) and usa_ablation_verdicts.csv. Fitted models are saved under
data/cache/usa_ablation/models (a stopped stage resumes without refitting), 2024 chances under data/cache/usa_ablation.
"""
import argparse
import json
import re
import time

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score as ap

from ml import data, models, place_extra
from ml import forecast_test as ft
from ml.moving_window import FEATURES_V1 as FEATURES
from ml.moving_window import PARAMS_V1 as PARAMS
from ml.moving_window import THRESHOLD_PCT
from ml.uncertainty import day_weights, interval, pr_auc_resamples, storm_day

TRAIN_YEARS, VAL_YEAR, LEAD, AGE = [2020, 2021, 2022, 2023], 2024, ft.LEAD, 2
SEEDS, FOLDS = range(3), 5
# E55 started from the Missouri + Illinois recipe (moving_window.FEATURES_V1, PARAMS_V1, forecast_test.WINDOW_V1);
# the pipeline's headline has since become its result, so this file pins its own starting point
WINDOW = ft.WINDOW_V1
BASE = data.resolve_features(FEATURES) + WINDOW
SIZES = {                                      # name: changes to PARAMS
    "current (depth 4, min child 20, 800 trees)": {},
    "depth 6": {"max_depth": 6},
    "depth 8": {"max_depth": 8},
    "depth 6, min child 100": {"max_depth": 6, "min_child_weight": 100},
    "depth 6, 1600 trees": {"max_depth": 6, "n_estimators": 1600},
    "depth 8, min child 100, 1600 trees": {"max_depth": 8, "min_child_weight": 100, "n_estimators": 1600},
}
DURATION = ["win_gust_hours15", "win_gust_hours20", "win_gust_mean", "win_gust_median", "win_gustiness_max"]
GROUPS = {
    "duration / spread": DURATION,
    "roads + street canopy": ["log_road_per_customer", "road_treed_share", "road_canopy_mean_pct"],
    "history": data.FEATURE_GROUPS["history"],
    "location": ["lat", "lon"],
    "E47 place groups": place_extra.all_groups(),
    "monotone gust": [],
}
MONOTONE = ["gust_max_ms", "win_gust_max_ms", "win_wind10_max_ms", "win_wind_squared"]
GUST_EDGES = [10, 15, 20, 25, 30, 35]          # m/s: the window's forecast max gust, binned for the threshold rules
PRIOR = 200                                    # decisions: how strongly a county's gust-bin rate leans on the nation's
BASELINES = {                                  # name: (model kind, features)
    "gust bins per county": ("county_gust", ["region_fips", "gust_bin"]),
    "gust bins, national": ("rate", ["gust_bin"]),
    "weather only (XGBoost)": ("xgboost", data.resolve_features("weather") + WINDOW),
    "warnings + outlook": ("rate", list(models.NEEDS_COLUMNS["official"])),
}
REFERENCE = "reference"


class CountyGustRate:
    """The strongest 'weather + threshold' rule: each county's own new-outage rate at each forecast gust level,
    shrunk toward the national rate at that level by PRIOR decisions (a county with few windy hours, or none in
    training, gets about the national rate): p = (outages + PRIOR x national) / (decisions + PRIOR), weighted."""

    def fit(self, X, y, sample_weight=None):
        w = np.ones(len(y)) if sample_weight is None else np.asarray(sample_weight, dtype=float)
        f = pd.DataFrame({"region_fips": X.region_fips.to_numpy(), "gust_bin": X.gust_bin.to_numpy(),
                          "wy": w * np.asarray(y, dtype=float), "w": w})
        nat = f.groupby("gust_bin")[["wy", "w"]].sum()
        self.national_ = (nat.wy / nat.w).rename("national")
        self.county_ = f.groupby(["region_fips", "gust_bin"])[["wy", "w"]].sum().reset_index()
        self.overall_ = float(f.wy.sum() / f.w.sum())
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        q = X[["region_fips", "gust_bin"]].merge(self.county_, on=["region_fips", "gust_bin"], how="left")
        q = q.merge(self.national_.reset_index(), on="gust_bin", how="left")
        nat = q.national.fillna(self.overall_).to_numpy()
        p = (q.wy.fillna(0).to_numpy() + PRIOR * nat) / (q.w.fillna(0).to_numpy() + PRIOR)
        return np.column_stack([1 - p, p])
OUT_DIR = data.ROOT / "data" / "cache" / "usa_ablation"
RESULTS = data.ROOT / "ml" / "results"
SCORES, VERDICTS = RESULTS / "usa_ablation_2024.csv", RESULTS / "usa_ablation_verdicts.csv"
SMOKE = False


# ---------- inputs ----------

def duration(h, by):
    """The duration / spread inputs from hourly gusts and wind, summarized over `by` (a rolling or groupby)."""
    return pd.DataFrame({
        "win_gust_hours15": by["g15"].sum(), "win_gust_hours20": by["g20"].sum(),
        "win_gust_mean": by["gust_ms"].mean(), "win_gust_median": by["gust_ms"].median(),
        "win_gustiness_max": by["gustiness"].max(),
    })


def hourly_gusts(h):
    h = h[["region_fips", *(c for c in ("hour", "run", "fhour") if c in h), "gust_ms", "wind10_ms"]].copy()
    h["g15"] = (h.gust_ms >= 15).astype("float32").where(h.gust_ms.notna())
    h["g20"] = (h.gust_ms >= 20).astype("float32").where(h.gust_ms.notna())
    h["gustiness"] = h.gust_ms - h.wind10_ms
    return h


def duration_actual(year, states=None):
    """Per decision of `year`: duration / spread over hours h + LEAD ... h + LEAD + 5 of the weather that actually
    happened. Built a state at a time for the whole country, cached (data.cached), read back for `states`."""
    def build():
        parts = []
        for s in data.warehouse_states()[:2] if SMOKE else data.warehouse_states():
            h = hourly_gusts(ft.actual_hourly([year], states=[s], until=f"{year + 1}-01-02"))
            for fips, r in h.groupby("region_fips"):
                r = r.set_index("hour").sort_index()
                r = r.reindex(pd.date_range(r.index.min(), r.index.max(), freq="h"))
                d = duration(r, r[["gust_ms", "g15", "g20", "gustiness"]].rolling(6, min_periods=6))
                d.index = d.index - pd.Timedelta(hours=LEAD + 5)
                parts.append(d[d.index.year == year].assign(region_fips=fips, state=s))
        return data.shrink(pd.concat(parts).rename_axis("block_start").reset_index())
    d = data.cached("duration_window", {"year": year, "lead": LEAD, "smoke": SMOKE}, build,
                    code_files=(data.__file__, __file__), filters=[("state", "in", list(states))] if states else None)
    return d.drop(columns="state")


def duration_forecast(f, age=AGE):
    """Per decision: duration / spread from the run issued `age` hours before it (as ft.window_from_forecast)."""
    first = age + LEAD
    g = hourly_gusts(f[f.fhour.between(first, first + 5)])
    cols = ["gust_ms", "g15", "g20", "gustiness"]
    d = duration(g, g[["region_fips", "run", *cols]].groupby(["region_fips", "run"])).reset_index()
    d["block_start"] = d.pop("run") + pd.Timedelta(hours=age)
    return d


_STATIC = {}


def static_inputs():
    """Per county: roads, location and the E47 place files; per county and year: history (as of Jan 1)."""
    if not _STATIC:
        roads = pd.read_csv(data.ROOT / "data" / "raw" / "place" / "roads.csv", dtype={"region_fips": str})
        geo = pd.read_csv(data.ROOT / "data" / "raw" / "geo" / "regions_study.csv", dtype={"region_fips": str})
        county = roads[["region_fips", "road_km", "road_treed_share", "road_canopy_mean_pct"]].merge(
            geo[["region_fips", "lat", "lon"]], on="region_fips", how="outer")
        con = duckdb.connect(str(data.DB), read_only=True)
        hist = con.sql("""SELECT region_fips, as_of_year, hours_out_per_customer AS hist_hours_out_per_customer,
                                 events_per_year AS hist_events_per_year, storm_hit_rate AS hist_storm_hit_rate,
                                 quiet_event_rate AS hist_quiet_event_rate, repeat_7d_share AS hist_repeat_7d_share
                          FROM marts.mart_study__region_history_asof""").df()
        con.close()
        hist["region_fips"] = hist.region_fips.astype(str)
        _STATIC["county"], _STATIC["history"] = county, hist
    return _STATIC["county"], _STATIC["history"]


def add_inputs(df):
    """Every candidate input that doesn't depend on the weather source, joined onto modeling rows."""
    county, hist = static_inputs()
    df = df.drop(columns=[c for c in data.static_columns() if c in df])   # data.add_static's: joined again here
    df["region_fips"] = df.region_fips.astype(str)
    df = df.merge(county, on="region_fips", how="left")
    df["log_road_per_customer"] = np.log10(df.pop("road_km")) - df.log_customers
    df["as_of_year"] = df.block_start.dt.year
    df = df.merge(hist, on=["region_fips", "as_of_year"], how="left").drop(columns="as_of_year")
    df = place_extra.add_place(df)
    df["gust_bin"] = np.digitize(df.win_gust_max_ms.to_numpy(), GUST_EDGES).astype("int8")
    new = [c for g in GROUPS.values() for c in g]
    return df.astype({c: "float32" for c in new if c in df and df[c].dtype != "float32"})


def add_train(df, year):
    """One training year: the actual window weather, its duration / spread, and the other inputs."""
    df = ft.add_actual_window(df, year).drop(columns=DURATION)      # forecast_test's: computed again here
    df = df.merge(duration_actual(year), on=["region_fips", "block_start"], how="left")
    return add_inputs(df)


def train_rows():
    states = data.warehouse_states()[:2] if SMOKE else None
    years = [2023] if SMOKE else TRAIN_YEARS
    df = data.sampled_years(THRESHOLD_PCT, years, LEAD, add=add_train, **({"states": states} if SMOKE else {}))
    return df[df.win_gust_max_ms.notna()].reset_index(drop=True)


def val_states():
    """2024 a state at a time: every decision with the newest run's window weather (and its duration / spread)."""
    states = data.warehouse_states()[:2] if SMOKE else data.warehouse_states()
    for s in states:
        f = ft.forecasts(f"{VAL_YEAR - 1}-12-31", f"{VAL_YEAR}-12-31", states=[s])
        if f.empty:
            continue
        w = ft.window_from_forecast(f, AGE).drop(columns=DURATION)      # forecast_test's: computed again here
        w = w.merge(duration_forecast(f, AGE), on=["region_fips", "block_start"])
        del f
        rows = data.load_hourly(THRESHOLD_PCT, [VAL_YEAR], LEAD, states=[s], float32=True)
        rows["region_fips"] = rows.region_fips.astype(str)
        rows = rows.merge(w, on=["region_fips", "block_start"], how="inner")
        rows = add_inputs(rows[rows.win_gust_max_ms.notna()].reset_index(drop=True))
        print(f"{data.STATE_ABBR.get(s, s)}: {len(rows):,} decisions of {VAL_YEAR}", flush=True)
        yield rows


# ---------- fitting and scoring ----------

def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def arm_params(base_params, arm):
    p = dict(base_params)
    if arm == "monotone gust":
        p["monotone_constraints"] = {c: 1 for c in MONOTONE}
    if SMOKE:
        p["n_estimators"] = 5
    return p


def fit_all(stage, arms, train, folds):
    """arms: {name: (params, features)}. Each over the seeds, and (if folds) seed 0 over the held-out folds. Models
    are saved and reloaded, so a stopped stage resumes."""
    out_dir = OUT_DIR / "models" / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    regions = sorted(train.region_fips.unique(), key=lambda fips: fips[::-1])   # neighbours in different folds
    fold_of = {fips: i % folds for i, fips in enumerate(regions)} if folds else {}
    fitted, t0 = {}, time.time()
    for name, (params, features) in arms.items():
        kind = params.get("_model", "xgboost")
        if kind != "xgboost":                  # a rate table: deterministic, fitted in seconds, never saved
            m = CountyGustRate() if kind == "county_gust" else models.RateBaseline(by=tuple(features))
            m.fit(train[features], train.y, sample_weight=train.weight)
            fitted[(name, "seed0")] = (m, features)
            print(f"fitted {name} ({time.time() - t0:.0f}s)", flush=True)
            continue
        jobs = [(f"seed{s}", s, None) for s in (SEEDS if not SMOKE else [0])] + \
               [(f"fold{k}", 0, k) for k in range(folds)]
        for setup, seed, fold in jobs:
            path = out_dir / f"{slug(name)}_{setup}.json"
            m = models.build("xgboost", params | {"random_state": seed})
            if path.exists():
                m.load_model(path)
            else:
                t = train if fold is None else train[train.region_fips.map(fold_of) != fold]
                m.fit(t[features], t.y, sample_weight=t.weight)
                m.save_model(path)
            fitted[(name, setup)] = (m, features)
        print(f"fitted {name} ({time.time() - t0:.0f}s)", flush=True)
    return fitted, fold_of


def score_2024(stage, fitted, fold_of):
    """Every fitted model's chance for every 2024 decision, a state at a time; seed models score every row, fold models
    only their own held-out counties. Saved to data/cache/usa_ablation/<stage>_2024.parquet."""
    parts = []
    for rows in val_states():
        out = rows[["region_fips", "block_start", "y"]].copy()
        fold = rows.region_fips.map(fold_of).fillna(-1).to_numpy() if fold_of else None
        names = dict.fromkeys(n for n, _ in fitted)
        for name in names:
            for (n, setup), (m, features) in fitted.items():
                if n != name:
                    continue
                if setup.startswith("seed"):
                    out[f"{name}|{setup}"] = m.predict_proba(rows[features])[:, 1].astype("float32")
                else:
                    k = int(setup[4:])
                    col = f"{name}|held-out"
                    if col not in out:
                        out[col] = np.float32(np.nan)
                    if (fold == k).any():
                        out.loc[fold == k, col] = m.predict_proba(rows.loc[fold == k, features])[:, 1]
        parts.append(out)
        del rows
    pred = pd.concat(parts, ignore_index=True)
    pred.to_parquet(OUT_DIR / f"{stage}_2024.parquet", index=False)
    return pred


def judge(stage, pred, pairs):
    """pairs: {arm: reference arm}. Scores and verdicts by the rule in the docstring; appended to the results files."""
    day = ((storm_day(pred.block_start) - storm_day(pred.block_start).min()).dt.days).to_numpy()
    counts, _ = day_weights(np.arange(day.max() + 1))
    names = list(dict.fromkeys([*pairs.values(), *pairs]))
    seeds = {n: [c for c in pred if c.startswith(f"{n}|seed")] for n in names}
    mean = {n: pred[seeds[n]].mean(axis=1).to_numpy() for n in names}
    boot = {n: pr_auc_resamples(pred.y, mean[n], day, counts) for n in names}
    scores, verdicts = [], []
    for n in names:
        for c in seeds[n]:
            scores.append({"stage": stage, "arm": n, "setup": c.split("|")[1], "onset_pr_auc": ap(pred.y, pred[c])})
        scores.append({"stage": stage, "arm": n, "setup": "seed mean", "onset_pr_auc": ap(pred.y, mean[n])})
        if f"{n}|held-out" in pred:
            ok = pred[f"{n}|held-out"].notna()
            scores.append({"stage": stage, "arm": n, "setup": "held-out counties",
                           "onset_pr_auc": ap(pred.y[ok], pred.loc[ok, f"{n}|held-out"])})
    by = pd.DataFrame(scores).set_index(["arm", "setup"]).onset_pr_auc
    for n, ref in pairs.items():
        lo, hi = interval(boot[n] / boot[ref] - 1)
        better = sum(by[(n, c.split("|")[1])] > by[(ref, c.split("|")[1])] for c in seeds[n])
        v = {"stage": stage, "arm": n, "reference": ref, "pr_auc": by[(n, "seed mean")],
             "reference_pr_auc": by[(ref, "seed mean")], "gain": by[(n, "seed mean")] / by[(ref, "seed mean")] - 1,
             "gain_lo": lo, "gain_hi": hi, "seeds_better": int(better), "seeds": len(seeds[n])}
        if (n, "held-out counties") in by and (ref, "held-out counties") in by:
            v["held_out_gain"] = by[(n, "held-out counties")] / by[(ref, "held-out counties")] - 1
        v["kept"] = bool(lo > 0 and better >= min(2, len(seeds[n])))
        verdicts.append(v)
    for path, new in ((SCORES, pd.DataFrame(scores)), (VERDICTS, pd.DataFrame(verdicts))):
        if SMOKE:
            path = OUT_DIR / path.name
        old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["stage"])
        pd.concat([old[old.stage != stage], new], ignore_index=True).to_csv(path, index=False)
    out = pd.DataFrame(verdicts)
    print(out.round(4).to_string(index=False), flush=True)
    return out


def chosen_size():
    """The size stage's choice: the highest-scoring setting that passed the rule, else the current settings."""
    v = pd.read_csv((OUT_DIR if SMOKE else RESULTS) / VERDICTS.name)
    v = v[(v.stage == "size") & v.kept]
    name = v.sort_values("pr_auc").arm.iloc[-1] if len(v) else next(iter(SIZES))
    return name, PARAMS | SIZES[name]


def run(stage):
    t0 = time.time()
    if stage == "baselines":
        arms = {REFERENCE: (arm_params(PARAMS, REFERENCE), BASE)}
        arms |= {b: ({"_model": kind} if kind != "xgboost" else arm_params(PARAMS, b), f)
                 for b, (kind, f) in BASELINES.items()}
        pairs = {b: REFERENCE for b in BASELINES}             # gain < 0: the baseline is worse than the model
        folds = 0
    elif stage == "size":
        arms = {n: (arm_params(PARAMS | p, n), BASE) for n, p in SIZES.items()}
        pairs = {n: next(iter(SIZES)) for n in list(SIZES)[1:]}
        folds = 0
    else:
        size, params = chosen_size()
        print(f"settings from the size stage: {size}", flush=True)
        if stage == "inputs":
            arms = {REFERENCE: (arm_params(params, REFERENCE), BASE)}
            arms |= {g: (arm_params(params, g), BASE + [c for c in cols if c not in BASE])
                     for g, cols in GROUPS.items()}
            pairs = {g: REFERENCE for g in GROUPS}
        else:
            v = pd.read_csv((OUT_DIR if SMOKE else RESULTS) / VERDICTS.name)
            kept = v[(v.stage == "inputs") & v.kept].arm.tolist()
            print(f"kept input groups: {kept or 'none'}", flush=True)
            features = BASE + list(dict.fromkeys(c for g in kept for c in GROUPS[g] if c not in BASE))
            p = arm_params(params, "monotone gust" if "monotone gust" in kept else REFERENCE)
            deeper = p | {"max_depth": p["max_depth"] + 2}
            longer = p | {"n_estimators": p["n_estimators"] * 2}
            arms = {REFERENCE: (arm_params(params, REFERENCE), BASE), "kept together": (p, features),
                    "kept together, depth + 2": (deeper, features), "kept together, 2x trees": (longer, features)}
            pairs = {"kept together": REFERENCE, "kept together, depth + 2": "kept together",
                     "kept together, 2x trees": "kept together"}
        folds = 2 if SMOKE else FOLDS
    train = train_rows()
    print(f"training rows: {len(train):,}, {int(train.y.sum()):,} new outages ({time.time() - t0:.0f}s)", flush=True)
    fitted, fold_of = fit_all(stage, arms, train, folds)
    del train
    pred = score_2024(stage, fitted, fold_of)
    print(f"2024: {len(pred):,} decisions, {int(pred.y.sum()):,} new outages ({time.time() - t0:.0f}s)", flush=True)
    judge(stage, pred, pairs)
    (OUT_DIR / f"{stage}_meta.json").write_text(json.dumps(
        {"stage": stage, "arms": {n: {"params": {k: v for k, v in p.items() if k != "monotone_constraints"},
                                      "monotone": "monotone_constraints" in p, "n_inputs": len(f)}
                                  for n, (p, f) in arms.items()},
         "seconds": round(time.time() - t0)}, indent=2))


def report():
    v = pd.read_csv(VERDICTS)
    print(v.round(4).to_string(index=False))


def main():
    global OUT_DIR, SMOKE
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["baselines", "size", "inputs", "combine", "report"])
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        SMOKE, OUT_DIR = True, OUT_DIR.with_name("usa_ablation_smoke")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report() if args.stage == "report" else run(args.stage)


if __name__ == "__main__":
    main()
