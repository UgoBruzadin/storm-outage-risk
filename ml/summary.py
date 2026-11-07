"""The headline numbers from ml/results/, next to the same numbers in the last commit: what changed in a run.

Usage: pixi run python -m ml.summary   (ml/pipeline.py runs it at the end)
Writes ml/results/summary.md.
"""
import io
import subprocess

import numpy as np
import pandas as pd

from ml import data

RESULTS = data.ROOT / "ml" / "results"
OUT = RESULTS / "summary.md"


def read(name, committed):
    """A results file now, or as last committed (None when missing)."""
    if not committed:
        path = RESULTS / name
        return pd.read_csv(path) if path.exists() else None
    git = subprocess.run(["git", "show", f"HEAD:ml/results/{name}"], cwd=data.ROOT, capture_output=True, text=True)
    return pd.read_csv(io.StringIO(git.stdout)) if git.returncode == 0 else None


def one(d, value, **where):
    for k, v in where.items():
        d = d[d[k] == v]
    return float(d[value].iloc[0]) if len(d) else np.nan


def numbers(committed):
    """(section, label, value, format) for every headline number."""
    out = []

    def add(section, label, fn, fmt="{:.2f}×"):
        try:
            v = fn()
        except Exception:                       # file missing, or written by an older version of the script
            v = np.nan
        out.append((section, label, v, fmt))

    ft, ens = read("forecast_test_2025.csv", committed), read("forecast_ensemble_2025.csv", committed)
    official = lambda: one(ft, "onset_pr_auc", model="warnings + outlook")  # noqa: E731
    add("Headline, 2025", "Counties", lambda: len(read("place_fragility.csv", committed)), "{:.0f}")
    add("Headline, 2025", "PR-AUC, model + five HRRR runs",
        lambda: one(ens, "onset_pr_auc", forecast="mean of the 5 runs"), "{:.3f}")
    add("Headline, 2025", "PR-AUC, warnings + outlook", official, "{:.3f}")
    add("Headline, 2025", "Ratio, model + five HRRR runs",
        lambda: one(ens, "onset_pr_auc", forecast="mean of the 5 runs") / official())
    add("Headline, 2025", "Ratio, no forecasts", lambda: one(ft, "onset_pr_auc", model="forecast-ready") / official())
    add("Headline, 2025", "Ratio, perfect weather (ceiling)",
        lambda: one(ft, "onset_pr_auc", model="+ window weather: actual") / official())

    years = read("extra_years.csv", committed)
    for y in (2022, 2023, 2024):
        add("Other test years", f"{y}, no forecasts",
            lambda y=y: one(years, "ratio", test_year=y, model="no forecasts"))
    add("Other test years", "Counties never trained on (2025)", lambda: one(read("extra_counties.csv", committed),
                                                                            "ratio"))

    st = read("midwest_2025.csv", committed)
    if st is not None:
        everything = [t for t in st.trained_on.unique() if t != "MO+IL"]
        for scored in st.scored_on.unique():
            add("By state (ratio, 95% range in the file)", f"{scored}, trained on {everything[0]}",
                lambda s=scored: one(st, "ratio", scored_on=s, trained_on=everything[0]))
        for scored in st.scored_on.unique():
            if scored not in ("MO", "IL", "MO+IL") and "+" in scored:
                add("By state (ratio, 95% range in the file)", f"{scored}, trained on MO+IL only (never seen)",
                    lambda s=scored: one(st, "ratio", scored_on=s, trained_on="MO+IL"))

    cov = read("coverage_2025.csv", committed)
    if cov is not None:
        for t in cov.trained_on.unique():
            add("Coverage (scored on all counties)", f"trained on {t}",
                lambda t=t: one(cov, "ratio", scored_on="all counties", trained_on=t))

    can = read("canopy_by_state.csv", committed)
    if can is not None:
        t = can[can.setup == "pooled"].pivot_table(index=["state", "seed"], columns="features", values="onset_pr_auc")
        effect = (t["with canopy"] / t["without canopy"] - 1).groupby(level=0).mean()
        for state, e in effect.items():
            add("Canopy in the model (PR-AUC change, 2024)", state, lambda e=e: e, "{:+.1%}")

    home = read("home_chance_2025.csv", committed)
    if home is not None:
        add("A typical home's chance (2025)", "Cross-entropy skill vs the usual month, model",
            lambda: one(home, "cross_entropy_skill", forecast="model"), "{:+.1%}")
        add("A typical home's chance (2025)", "Cross-entropy skill vs the usual month, warnings + outlook",
            lambda: one(home, "cross_entropy_skill", forecast="warnings"), "{:+.1%}")

    frag = read("place_fragility.csv", committed)
    if frag is not None:
        add("Beyond the weather", "Counties the outage data barely covers", lambda: (~frag.tracked).sum(), "{:.0f}")
    return out


def main():
    now, before = numbers(False), numbers(True)
    lines = ["# Results summary", "", "Written by `ml/summary.py`. Before = the last commit's `ml/results/`.", ""]
    section = None
    old = {(s, label): v for s, label, v, _ in before}
    for s, label, v, fmt in now:
        if s != section:
            lines += ["", f"## {s}", "", "| | now | before |", "|---|---|---|"]
            section = s
        b = old.get((s, label), np.nan)
        show = lambda x, fmt=fmt: "–" if pd.isna(x) else fmt.format(x)  # noqa: E731
        changed = "" if pd.isna(b) or pd.isna(v) or show(v) == show(b) else " **changed**"
        lines.append(f"| {label} | {show(v)}{changed} | {show(b)} |")
    OUT.write_text("\n".join(lines) + "\n")
    print(OUT.read_text())


if __name__ == "__main__":
    main()
