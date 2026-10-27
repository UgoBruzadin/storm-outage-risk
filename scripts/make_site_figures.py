"""Static figures for the project page (site/assets/), drawn from the same data as the dashboard.

  storm-replay.jpg    predicted risk vs actual outages, biggest 2025 storm block
  accuracy.jpg        per county, 2025: share of new outages caught, and actual vs expected
  map.jpg             outage hours per customer per year, 2020–2023 scorecard
  results.jpg         onset PR-AUC of the model, its ablations and the comparisons
  canopy-map.jpg      average tree canopy per region (USFS / NLCD 2021)
  canopy-scatter.jpg  canopy vs storm hit rate (2020–2023 scorecard), one dot per region

Reads data/app/ (pixi run export-app), ml/results/ and the warehouse (read-only).
Usage: pixi run python scripts/make_site_figures.py
Then bump the ?v= on the image links in site/index.html, or browsers keep showing the old files.
"""
import json
from pathlib import Path

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets"
APP = ROOT / "data" / "app"
RESULTS = ROOT / "ml" / "results"

SURFACE, INK, INK_2, MUTED, LINE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
HATCH = "#c3c2b7"                                               # hatching: counties with too little to judge
STATE = {"Illinois": "#2a78d6", "Missouri": "#eb6834"}          # categorical slots 1 and 2
# sequential ramps, light -> dark (the dashboard's, app/lib.py)
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORANGE = ["#fde0d2", "#f8b998", "#f2925f", "#eb6834", "#c84f1f", "#9c3c16", "#6e2a0f"]
GREEN = ["#eef6ee", "#a9d4a9", "#4fa64f", "#008300", "#004d00"]
# diverging: blue (fewer than expected) <- gray -> orange (more than expected)
DIVERGING = ["#184f95", "#6da7ec", "#f0efec", "#f2925f", "#9c3c16"]
LABELS = {"29203": "Shannon", "17019": "Champaign", "29189+29510": "St. Louis", "17031": "Cook"}
MIN_EVENTS = 3          # as in the dashboard's Accuracy tab

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 11,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": LINE, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def cmap(colors):
    return LinearSegmentedColormap.from_list("ramp", colors)


def load():
    con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
    scores = con.sql("""
        SELECT region_fips, region, state, canopy_mean_pct, storm_hit_rate, hours_out_per_customer
        FROM marts.mart_study__region_resilience
    """).df()
    con.close()
    shapes = gpd.read_parquet(ROOT / "data" / "raw" / "geo" / "regions_study.parquet")[["region_fips", "geometry"]]
    return shapes.merge(scores, on="region_fips").to_crs(5070)    # equal-area projection for the maps


def county_map(ax, gdf, column, colors, vmin, vmax, judged=None):
    """Counties colored by `column`; counties outside `judged` hatched (never a color the scale uses);
    state lines on top."""
    shown = gdf if judged is None else gdf[judged]
    if judged is not None:
        gdf[~judged].plot(ax=ax, facecolor=SURFACE, edgecolor=HATCH, hatch="////", linewidth=0.4)
    shown.plot(column=column, cmap=cmap(colors), vmin=vmin, vmax=vmax, ax=ax, edgecolor=SURFACE, linewidth=0.5)
    gdf.dissolve("state").boundary.plot(ax=ax, color=INK_2, linewidth=0.8)
    minx, miny, maxx, maxy = gdf.total_bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_axis_off()


ASPECT = 0.96           # width / height of Missouri + Illinois in EPSG:5070


def map_figure(panels):
    """`panels` side-by-side maps in boxes sized to the study area's shape, so titles sit on the
    map's left edge with no gap, and a color bar under each."""
    fig_w, fig_h = (11.0, 6.6) if panels == 2 else (6.4, 7.4)
    map_h = 0.64 if panels == 2 else 0.70           # share of figure height; room above for two titles
    map_w = map_h * fig_h * ASPECT / fig_w           # same shape as the map
    gap = (1 - panels * map_w) / (panels + 1)
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=200)
    axes, bars = [], []
    for i in range(panels):
        left = gap + i * (map_w + gap)
        axes.append(fig.add_axes([left, 0.19, map_w, map_h]))
        bars.append(fig.add_axes([left + map_w * 0.1, 0.13, map_w * 0.8, 0.022]))
    return fig, axes, bars


def colorbar(fig, cax, colors, vmin, vmax, label, ticks=None, ticklabels=None):
    bar = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap(colors), norm=plt.Normalize(vmin, vmax)), cax=cax,
                       orientation="horizontal")
    bar.set_label(label, color=INK_2, fontsize=10)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=9, color=LINE)
    if ticks is not None:
        bar.set_ticks(ticks, labels=ticklabels)
    return bar


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.15, pil_kwargs={"quality": 90})
    plt.close(fig)


def storm_replay(gdf, preds, storms, meta):
    block = storms.sort_values("customers_out", ascending=False).block_start.iloc[0]
    now = gdf.merge(preds[preds.block_start == block], on="region_fips")
    vmax_p = max(2 * meta["alert_threshold"], now.prob.max())
    vmax_o = max(10, now.peak_pct_out.max())
    fig, (a, b), (ca, cb) = map_figure(2)
    county_map(a, now, "prob", BLUE, 0, vmax_p)
    county_map(b, now, "peak_pct_out", ORANGE, 0, vmax_o)
    ticks = np.arange(0, vmax_p + 1e-9, 0.2)
    colorbar(fig, ca, BLUE, 0, vmax_p, "Predicted probability of ≥ 5% out", ticks, [f"{t:.0%}" for t in ticks])
    colorbar(fig, cb, ORANGE, 0, vmax_o, "Actual peak share of customers out (%)")
    a.set_title("Predicted risk", loc="left", fontsize=13, fontweight="bold")
    b.set_title("What happened", loc="left", fontsize=13, fontweight="bold")
    when = pd.Timestamp(block)
    fig.suptitle(f"{when:%-d %B %Y}, {when:%H}–{when + pd.Timedelta(hours=6):%H} UTC: a storm the model never saw",
                 x=fig.axes[0].get_position().x0, ha="left", fontsize=15, fontweight="bold", y=0.985)
    save(fig, "storm-replay.jpg")


def accuracy(gdf, preds, meta):
    onsets = preds[preds.is_onset].assign(flagged=lambda d: d.prob >= meta["onset_alert_threshold"])
    onsets["caught"] = onsets.flagged & (onsets.y == 1)
    stats = onsets.groupby("region_fips").agg(new=("y", "sum"), expected=("prob", "sum"), caught=("caught", "sum"))
    df = gdf.merge(stats.reset_index(), on="region_fips", how="left").fillna({"new": 0, "caught": 0})
    df["share_caught"] = df.caught / df.new.where(df.new > 0)
    df["log_ratio"] = np.log2((df.new / df.expected).clip(0.25, 4))
    judged = df.new >= MIN_EVENTS
    fig, (a, b), (ca, cb) = map_figure(2)
    county_map(a, df, "share_caught", BLUE, 0, 1, judged)
    county_map(b, df, "log_ratio", DIVERGING, -2, 2, judged)
    colorbar(fig, ca, BLUE, 0, 1, "Share of new outages flagged", [0, 0.25, 0.5, 0.75, 1],
             ["0%", "25%", "50%", "75%", "100%"])
    colorbar(fig, cb, DIVERGING, -2, 2, "Actual ÷ expected new outages", [-2, -1, 0, 1, 2],
             ["¼×", "½×", "1×", "2×", "4×"])
    total = int(df.new.sum())
    a.set_title(f"Caught: {df.caught.sum() / total:.0%} of {total:,} new outages", loc="left", fontsize=13,
                fontweight="bold")
    b.set_title("Underrated (orange) or overrated (blue)", loc="left", fontsize=13, fontweight="bold")
    x0 = a.get_position().x0
    fig.suptitle(f"Accuracy by county, {meta['test_year']}", x=x0, ha="left", fontsize=15, fontweight="bold",
                 y=0.985)
    fig.text(x0, 0.015, f"New outages of ≥ {meta['threshold_pct']:g}% of customers. Hatched: fewer than "
             f"{MIN_EVENTS} in the county, too few to judge.", color=MUTED, fontsize=9)
    save(fig, "accuracy.jpg")


def burden_map(gdf):
    fig, (ax,), (cax,) = map_figure(1)
    vmax = float(np.ceil(gdf.hours_out_per_customer.quantile(0.98)))
    county_map(ax, gdf, "hours_out_per_customer", BLUE, 0, vmax)
    colorbar(fig, cax, BLUE, 0, vmax, "Outage hours per customer per year")
    fig.suptitle("Outage burden by county, 2020–2023", x=ax.get_position().x0, ha="left", fontsize=14,
                 fontweight="bold", y=0.97)
    save(fig, "map.jpg")


def results():
    """Onset PR-AUC at >= 5%: this project's models against baselines and comparisons, both splits."""
    def scores(name):
        d = pd.read_csv(RESULTS / f"benchmark_{name}.csv")
        d["split"] = d["split"].str.split("(").str[0]
        return d[d.threshold_pct == 5]

    official, final, wn = scores("official"), scores("final_2025"), scores("weathernext")
    pick = [  # (label, frame, model, features, this project's)
        ("Historical average", official, "climatology", "-", False),
        ("NWS warnings", official, "nws_warnings", "-", False),
        ("SPC outlook", official, "spc_outlook", "-", False),
        ("Warnings + outlook", official, "official", "-", False),
        ("weathernext's setup", wn, "xgboost", "weathernext", False),
        ("Weather only", final, "xgboost", "weather", True),
        ("Final model", final, "xgboost", "weather+place+recent", True),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), dpi=200, sharey=True)
    for ax, split, title in zip(axes, ["time", "county"], ["Next year (2025)", "Unseen counties"], strict=True):
        vals, rate = [], None
        for label, d, model, features, ours in pick:
            row = d[(d.split == split) & (d.model == model) & (d.features == features)].iloc[0]
            vals.append((label, row.onset_pr_auc, ours))
            rate = row.onset_event_rate
        y = np.arange(len(vals))[::-1]
        ax.barh(y, [v for _, v, _ in vals], height=0.68, color=[BLUE[4] if o else "#c3c2b7" for *_, o in vals],
                edgecolor=SURFACE, linewidth=2)
        for yi, (_, v, _) in zip(y, vals, strict=True):
            ax.text(v + 0.002, yi, f"{v:.3f}", va="center", fontsize=10, color=INK)
        ax.axvline(rate, color=MUTED, linestyle=":", linewidth=1.2)
        ax.text(rate, -0.85, " no skill", color=MUTED, fontsize=8.5, va="center")
        ax.set_ylim(-1.2, len(vals) - 0.5)
        ax.set_yticks(y, [label for label, *_ in vals], fontsize=10.5, color=INK)
        ax.set_xlim(0, 0.125)
        ax.set_title(title, loc="left", fontsize=13, fontweight="bold")
        ax.grid(axis="x", color=LINE, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel("PR-AUC on new ≥ 5% outages")
    fig.suptitle("The model against what's already available", x=0.02, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.02, -0.04, "Blue: this project's models. Gray: baselines and comparisons. Official forecasts as known "
             "at the block's start; the models see the block's weather.", color=MUTED, fontsize=9)
    fig.tight_layout()
    save(fig, "results.jpg")


def canopy_map(gdf):
    fig, (ax,), (cax,) = map_figure(1)
    county_map(ax, gdf, "canopy_mean_pct", GREEN, 0, 75)
    for fips, name in LABELS.items():
        row = gdf[gdf.region_fips == fips].iloc[0]
        pt = row.geometry.representative_point()
        ax.annotate(f"{name}\n{row.canopy_mean_pct:.0f}%", (pt.x, pt.y), ha="center", va="center", fontsize=9,
                    color=INK, bbox={"boxstyle": "round,pad=0.25", "fc": SURFACE, "ec": LINE, "lw": 0.6})
    colorbar(fig, cax, GREEN, 0, 75, "Average tree canopy cover (%)")
    fig.suptitle("Tree canopy by county", x=ax.get_position().x0, ha="left", fontsize=14, fontweight="bold",
                 y=0.97)
    save(fig, "canopy-map.jpg")


def canopy_scatter(gdf):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    for state, color in STATE.items():
        rows = gdf[gdf.state == state]
        r = np.corrcoef(rows.canopy_mean_pct, rows.storm_hit_rate)[0, 1]
        ax.scatter(rows.canopy_mean_pct, rows.storm_hit_rate * 100, s=42, color=color, alpha=0.85,
                   edgecolor=SURFACE, linewidth=1.2, label=f"{state} (r = {r:+.2f})", zorder=3)
    r = np.corrcoef(gdf.canopy_mean_pct, gdf.storm_hit_rate)[0, 1]
    ax.grid(color=LINE, linewidth=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("Average tree canopy cover (%)")
    ax.set_ylabel("Storm hit rate (%)")
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.2,
              handletextpad=0.3, columnspacing=1.2)
    fig.suptitle(f"More trees, not clearly more outages (r = {r:.2f})", x=0.125, y=1.0, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(0.01, -0.02, "One dot per county. Storm hit rate: share of blocks with a NOAA storm report that had "
             "≥ 1% of customers out, 2020–2023.", color=MUTED, fontsize=8.5)
    save(fig, "canopy-scatter.jpg")


if __name__ == "__main__":
    gdf = load()
    preds = pd.read_parquet(APP / "predictions.parquet")
    meta = json.loads((APP / "meta.json").read_text())
    storm_replay(gdf, preds, pd.read_parquet(APP / "storms.parquet"), meta)
    accuracy(gdf, preds, meta)
    burden_map(gdf)
    results()
    canopy_map(gdf)
    canopy_scatter(gdf)
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.jpg"))))
