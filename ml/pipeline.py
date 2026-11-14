"""Every experiment behind a number on the story page, in order, for whatever states dbt/seeds/study_states.csv lists.

A step runs when one of its outputs is missing or older than an output of a step it needs (or the warehouse), like
make. After a change to the data (pixi run build) everything downstream runs again; after a change to one script,
pass --from <step>. Each step's output is logged to data/pipeline_logs/<step>.log, and the run ends with
ml/results/summary.md: the headline numbers next to the ones last committed.

Usage:
  pixi run pipeline [--dry-run] [--from STEP] [--only STEP,STEP] [--force]
  pixi run pipeline --smoke   every step on Missouri + Illinois with 5 trees, in data/smoke/root (ml/smoke.py):
                              minutes, never the real results; run it before a long run
  pixi run pipeline --list
The data itself (downloads and dbt) is `pixi run data`; this starts from the warehouse.
"""
import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO                    # the tree whose outputs are checked and written (--smoke: data/smoke/root)
WAREHOUSE = "data/warehouse.duckdb"


@dataclass
class Step:
    name: str
    cmd: str
    outputs: list[str]
    needs: list[str] = field(default_factory=list)
    about: str = ""


PY = "python -m"
STEPS = [
    # first: every input is what it claims (recomputed from the raw tables for 20,000 decisions); fails on any mismatch
    Step("audit", f"{PY} ml.audit --checks timing", ["ml/results/audit_timing.csv"],
         about="every input and the label recomputed from the raw tables, with explicit time filters"),
    # the headline and the results ladder
    Step("moving_window", f"{PY} ml.moving_window", ["ml/results/moving_window_2025.csv"],
         about="the model by lead time, observed weather only"),
    Step("forecast_test", f"{PY} ml.forecast_test",
         ["ml/results/forecast_test_2025.csv", "data/cache/forecast_test_2025_predictions.parquet"],
         about="2025 with HRRR forecasts of the window: the headline"),
    Step("forecast_ensemble", f"{PY} ml.forecast_ensemble",
         ["ml/results/forecast_ensemble_2025.csv", "ml/results/forecast_ensemble_bins_2025.csv",
          "data/cache/forecast_ensemble_2025.parquet", "data/cache/forecast_ensemble_all_2025.parquet"],
         needs=["forecast_test"], about="the five HRRR runs: mean and range"),
    Step("display_model", f"{PY} ml.display_model", ["data/cache/display_2025.parquet"],
         needs=["forecast_ensemble"], about="chances drawn on the story page's maps"),
    Step("calibrate", f"{PY} ml.calibrate_forecasts",
         ["ml/results/calibration_forecasts_2025.csv", "ml/results/value_forecasts_2025.csv"],
         needs=["forecast_ensemble"]),
    Step("value_hourly", f"{PY} ml.value_hourly", ["ml/results/value_hourly_2025.csv"], needs=["moving_window"],
         about="what staging crews on each forecast was worth"),
    Step("significance", f"{PY} ml.significance", ["ml/results/significance_2025.csv"],
         needs=["forecast_test", "forecast_ensemble"]),
    Step("benchmark_final", f"{PY} ml.benchmark ml/benchmarks/final_2025.yaml",
         ["ml/results/benchmark_final_2025.csv"], about="persistence and the day-level models"),
    # does it hold up
    Step("extra", f"{PY} ml.extra_analyses --only years,storm_types,counties",
         ["ml/results/extra_years.csv", "ml/results/extra_storm_types.csv", "ml/results/extra_counties.csv"],
         needs=["forecast_test", "forecast_ensemble"], about="other test years, kinds of storm, unseen counties"),
    Step("states", f"{PY} ml.midwest_test", ["ml/results/midwest_2025.csv"],
         about="state by state, and states the model never trained on"),
    Step("coverage", f"{PY} ml.coverage_test", ["ml/results/coverage_2025.csv"],
         about="the headline without the counties the outage data barely covers"),
    Step("home_chance", f"{PY} ml.home_chance",
         ["ml/results/home_chance_2025.csv", "ml/results/home_chance_calibration_2025.csv"],
         about="the chance a typical home in the county loses power"),
    # place
    Step("canopy_by_state", f"{PY} ml.canopy_by_state", ["ml/results/canopy_by_state.csv"]),
    Step("place_fragility", f"{PY} ml.place_fragility", ["ml/results/place_fragility.csv"],
         about="outages beyond the weather; roads and trees along them"),
    # what the page and the dashboard read
    Step("export_app", f"{PY} ml.export_app_data --config ml/benchmarks/final_2025.yaml",
         ["data/app/meta.json", "data/app/regions.parquet"], needs=["benchmark_final"]),
    Step("export_hourly", f"{PY} ml.export_hourly", ["data/app/meta_hourly.json", "data/app/ladder.parquet"],
         needs=["export_app", "moving_window", "forecast_test", "forecast_ensemble", "value_hourly"]),
    Step("site", "python scripts/make_site_figures.py --no-clip",
         ["data/site_preview/data/story.json"],
         needs=["audit", "export_hourly", "display_model", "calibrate", "significance", "extra", "canopy_by_state",
                "place_fragility", "states"],
         about="figures and story.json in data/site_preview/, never over site/ (no storm video)"),
]
BY_NAME = {s.name: s for s in STEPS}


def mtime(path):
    p = ROOT / path
    return p.stat().st_mtime if p.exists() else None


def stale(step, ran):
    """Missing an output, older than what it needs, or a step it needs ran in this run."""
    times = [mtime(o) for o in step.outputs]
    if None in times:
        return "missing " + step.outputs[times.index(None)]
    oldest = min(times)
    sources = [WAREHOUSE] + [o for n in step.needs for o in BY_NAME[n].outputs]
    newer = [s for s in sources if (mtime(s) or 0) > oldest]
    if newer:
        return f"older than {newer[0]}"
    if ran & set(step.needs):
        return f"{sorted(ran & set(step.needs))[0]} ran"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="say what would run, run nothing")
    ap.add_argument("--from", dest="start", help="run this step and every step after it")
    ap.add_argument("--only", help="comma-separated steps to run, whether stale or not")
    ap.add_argument("--force", action="store_true", help="run every step")
    ap.add_argument("--list", action="store_true", help="list the steps")
    ap.add_argument("--smoke", action="store_true", help="every step on two states with 5 trees (data/smoke/root)")
    a = ap.parse_args()
    global ROOT
    if a.smoke:
        from ml import smoke
        ROOT = smoke.prepare()
        smoke.reset()
        os.environ["STORM_ROOT"], os.environ["STORM_SMOKE"] = str(ROOT), "1"     # read by every step (ml/data.py)
        a.force = True
    logs = ROOT / "data" / "pipeline_logs"
    if a.list:
        for s in STEPS:
            print(f"{s.name:18s} {s.about or s.cmd}")
        return
    names = [s.name for s in STEPS]
    for n in ([a.start] if a.start else []) + (a.only.split(",") if a.only else []):
        if n not in BY_NAME:
            sys.exit(f"unknown step {n}; steps: {', '.join(names)}")
    forced = set(names[names.index(a.start):]) if a.start else set(a.only.split(",")) if a.only else set()
    logs.mkdir(parents=True, exist_ok=True)
    ran, failed = set(), []
    for s in STEPS:
        if a.only and s.name not in forced:
            continue
        why = "forced" if a.force or s.name in forced else stale(s, ran)
        if not why:
            print(f"  {s.name:18s} up to date")
            continue
        if bad := [n for n in s.needs if n in failed]:
            print(f"  {s.name:18s} skipped: {bad[0]} failed")
            failed.append(s.name)
            continue
        print(f"> {s.name:18s} {why}: {s.cmd}", flush=True)
        if a.dry_run:
            ran.add(s.name)
            continue
        t = time.time()
        with open(logs / f"{s.name}.log", "w") as log:
            code = subprocess.run(s.cmd, shell=True, cwd=REPO, stdout=log, stderr=subprocess.STDOUT).returncode
        mins = (time.time() - t) / 60
        if code:
            print(f"  {s.name:18s} FAILED after {mins:.0f} min, see {logs}/{s.name}.log", flush=True)
            failed.append(s.name)
        else:
            print(f"  {s.name:18s} done in {mins:.0f} min", flush=True)
            ran.add(s.name)
    if not a.dry_run:
        from ml import summary
        summary.main()
    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
