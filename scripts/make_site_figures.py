"""Static figures for the project page (site/assets/), drawn from the same data as the dashboard.

  accuracy.jpg        per county, 2025, 2 hours ahead: share of new outages caught, and actual vs predicted
  map.jpg             outage hours per customer per year, 2020–2025 scorecard
  results.jpg         onset PR-AUC 2 hours ahead with storm-day ranges, and by lead time
  canopy-map.jpg      average tree canopy per region (USFS / NLCD 2021)
  canopy-scatter.jpg  canopy vs storm hit rate (2020–2025 scorecard), one dot per region
  value.jpg           what staging crews on each forecast was worth in 2025 (ml/value_hourly.py)
  social.jpg          1200x630 link-preview card (og:image): the March 2025 storm, risk decided 2 hours ahead
  storm.mp4           the March 2025 storm hour by hour, for social posts
  site/data/story.json  everything the story page (site/index.html) draws: shapes, storm, results

Reads data/app/ (pixi run export-app, then python -m ml.export_hourly), ml/results/ and the warehouse
(read-only), and data/cache/forecast_ensemble_2025.parquet (python -m ml.forecast_ensemble).
Usage: pixi run python scripts/make_site_figures.py [--story]
Then bump the ?v= on the image links in site/writeup/index.html, or browsers keep showing the old files.
"""
import json
import subprocess
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


def accuracy(gdf):
    """Per county, 2025, the headline model (ml/export_hourly.py): share of new outages caught at the headline
    alert share, and actual outage windows against the sum of predicted probabilities."""
    meta = json.loads((APP / "meta_hourly.json").read_text())
    stats = pd.read_parquet(APP / "county_hourly.parquet")
    df = gdf.merge(stats, on="region_fips", how="left").fillna({"new_outages": 0, "caught": 0})
    df["share_caught"] = df.caught / df.new_outages.where(df.new_outages > 0)
    df["log_ratio"] = np.log2((df.actual / df.expected).clip(0.25, 4))
    judged = df.new_outages >= MIN_EVENTS
    fig, (a, b), (ca, cb) = map_figure(2)
    county_map(a, df, "share_caught", BLUE, 0, 1, judged)
    county_map(b, df, "log_ratio", DIVERGING, -2, 2, judged)
    colorbar(fig, ca, BLUE, 0, 1, "Share of new outages caught in time", [0, 0.25, 0.5, 0.75, 1],
             ["0%", "25%", "50%", "75%", "100%"])
    colorbar(fig, cb, DIVERGING, -2, 2, "Actual ÷ predicted outage windows", [-2, -1, 0, 1, 2],
             ["¼×", "½×", "1×", "2×", "4×"])
    total = int(df.new_outages.sum())
    a.set_title(f"Caught: {df.caught.sum() / total:.0%} of {total:,} new outages", loc="left", fontsize=13,
                fontweight="bold")
    b.set_title("Underrated (orange) or overrated (blue)", loc="left", fontsize=13, fontweight="bold")
    x0 = a.get_position().x0
    fig.suptitle(f"Accuracy by county, {meta['test_year']}, {meta['lead_hours']} hours ahead", x=x0, ha="left",
                 fontsize=15, fontweight="bold", y=0.985)
    fig.text(x0, 0.015, f"New outages of ≥ {meta['threshold_pct']:g}% of customers; alerts on the riskiest "
             f"{meta['headline_share']:.2%} of county-hours. Hatched: fewer than {MIN_EVENTS} new outages, too few "
             "to judge.", color=MUTED, fontsize=9)
    save(fig, "accuracy.jpg")


def burden_map(gdf):
    fig, (ax,), (cax,) = map_figure(1)
    vmax = float(np.ceil(gdf.hours_out_per_customer.quantile(0.98)))
    county_map(ax, gdf, "hours_out_per_customer", BLUE, 0, vmax)
    colorbar(fig, cax, BLUE, 0, vmax, "Outage hours per customer per year")
    fig.suptitle("Outage burden by county, 2020–2025", x=ax.get_position().x0, ha="left", fontsize=14,
                 fontweight="bold", y=0.97)
    save(fig, "map.jpg")


def results():
    """Left: onset PR-AUC 2 hours ahead with 95% storm-day ranges (ladder.parquet). Right: by lead time
    (moving_window_2025.csv), with the HRRR forecast version at 2 hours."""
    ladder = pd.read_parquet(APP / "ladder.parquet")
    lead = pd.read_parquet(APP / "lead_time.parquet")
    meta = json.loads((APP / "meta_hourly.json").read_text())
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=200, gridspec_kw={"width_ratios": [1.15, 1]})
    y = np.arange(len(ladder))[::-1]
    for yi, r in zip(y, ladder.itertuples(), strict=True):
        ours, ceiling = r.model == meta["headline_model"], "ceiling" in r.model
        color = BLUE[4] if ours else (HATCH if r.model == "Warnings + outlook" else BLUE[2])
        a.barh(yi, r.onset_pr_auc, height=0.62, color="none" if ceiling else color,
               edgecolor=MUTED if ceiling else SURFACE, linestyle="--" if ceiling else "-", linewidth=1.4)
        a.plot([r.lo, r.hi], [yi, yi], color=INK_2, linewidth=1.3)
        a.plot([r.lo, r.lo], [yi - 0.12, yi + 0.12], color=INK_2, linewidth=1.3)
        a.plot([r.hi, r.hi], [yi - 0.12, yi + 0.12], color=INK_2, linewidth=1.3)
        extra = "" if r.model == "Warnings + outlook" else f"  {r.ratio_vs_official:.1f}× official"
        a.text(r.hi + 0.003, yi, f"{r.onset_pr_auc:.3f}{extra}", va="center", fontsize=9.5, color=INK,
               fontweight="bold" if ours else "normal")
    a.set_yticks(y, [LADDER_LABELS[m] for m in ladder.model], fontsize=10, color=INK)
    a.set_xlim(0, 0.215)
    a.set_xlabel("PR-AUC on new ≥ 5% outages, 2 hours ahead (bars: 95% range)")
    a.set_title("How early can you know?", loc="left", fontsize=13, fontweight="bold")
    a.tick_params(axis="y", length=0)
    runs = [("Warnings + outlook (rate table)", "Warnings + outlook alone", HATCH),
            ("Model: weather + place + recent", "Model, weather so far only", ORANGE[3]),
            ("+ neighbours (final)", "Model + warnings + outlook", BLUE[4])]
    for run, label, color in runs:
        d = lead[lead.run == run].sort_values("lead_hours")
        b.plot(d.lead_hours, d.onset_pr_auc, marker="o", color=color, linewidth=2.2, markersize=5,
               markeredgecolor=SURFACE, label=label)
    f = ladder[ladder.model == meta["headline_model"]].iloc[0]
    b.scatter([2], [f.onset_pr_auc], s=90, color=BLUE[5], edgecolor=SURFACE, linewidth=1.5, zorder=4,
              label="Model + last five HRRR forecasts")
    b.set_xticks([0, 1, 2, 3, 6], ["0 h", "1 h", "2 h", "3 h", "6 h"])
    b.set_ylim(0, 0.11)
    b.set_xlabel("hours between the decision and the 6 hours it predicts")
    b.set_title("Looking further ahead", loc="left", fontsize=13, fontweight="bold")
    b.legend(frameon=False, fontsize=9, loc="lower left", labelcolor=INK)
    for ax in (a, b):
        ax.grid(axis="x" if ax is a else "y", color=LINE, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    a.spines["left"].set_visible(False)
    fig.suptitle(f"New outages, {meta['test_year']}: a year the model never saw", x=0.02, ha="left", fontsize=15,
                 fontweight="bold")
    fig.text(0.02, -0.04, "95% ranges from resampling 2025's storm days. Ratios to warnings + outlook are paired "
             "(same resampled days), so they are much firmer than any single score.", color=MUTED, fontsize=9)
    fig.tight_layout()
    save(fig, "results.jpg")


STORM_HOURS = pd.date_range("2025-03-14 18:00", "2025-03-15 21:00", freq="h")   # the story page's storm, UTC
THRESHOLD = 5
LADDER_LABELS = {"Warnings + outlook": "NWS warnings + SPC outlook alone",
                 "No forecasts": "Model, weather observed so far",
                 "With HRRR forecasts (newest run)": "Model + latest HRRR forecast",
                 "With HRRR forecasts (mean of 5 runs)": "Model + last five HRRR forecasts",
                 "Perfect weather (ceiling)": "Ceiling: knowing the weather in advance"}
HOURLY_VALUE = [  # (column in ml/results/value_hourly_2025.csv, label), drawn top to bottom
    ("perfect", "Perfect foresight"), ("model", "Model, weather observed so far"), ("official", "Warnings + outlook")]
def money(millions):
    """−14.9 -> '−\\$14.9M' (escaped: matplotlib reads a bare $ as math)."""
    if abs(millions) < 0.05:
        return "\\$0"
    return f"{'−' if millions < 0 else ''}\\${abs(millions):.1f}M"


def value_figure():
    """Net savings in 2025 from staging crews on alert episodes 2 hours ahead (ml/value_hourly.py), the four
    typical-customer-mix scenarios as dots on a range per forecast."""
    dollars = pd.read_csv(RESULTS / "value_hourly_2025.csv").query("mix == 'typical mix'")
    fig, b = plt.subplots(figsize=(10, 3.4), dpi=200)
    y = np.arange(len(HOURLY_VALUE))[::-1]
    for yi, (col, _) in zip(y, HOURLY_VALUE, strict=True):
        v = dollars[col] / 1e6
        color = BLUE[4] if col == "model" else (MUTED if col == "perfect" else HATCH)
        b.plot([v.min(), v.max()], [yi, yi], color=color, linewidth=7, solid_capstyle="round", alpha=0.45)
        b.scatter(v, [yi] * len(v), color=color, s=26, zorder=3, edgecolor=SURFACE, linewidth=1)
        if v.max() < 0:                       # all losses: label left of the range, clear of the zero line
            b.text(v.min() - 2, yi, f"{money(v.min())} to {money(v.max())}", va="center", ha="right", fontsize=9.5,
                   color=INK)
        else:
            b.text(v.max() + 2, yi, f"{money(v.min())} to {money(v.max())}", va="center", fontsize=9.5, color=INK)
    b.axvline(0, color=INK_2, linewidth=0.8)
    b.set_yticks(y, [label for _, label in HOURLY_VALUE], fontsize=10.5, color=INK)
    b.set_xlim(-55, 160)
    b.set_xlabel("net savings in 2025, $ millions (customer outage costs avoided − staging costs)")
    b.grid(axis="x", color=LINE, linewidth=0.6)
    b.set_axisbelow(True)
    b.tick_params(axis="y", length=0)
    for side in ("top", "right", "left"):
        b.spines[side].set_visible(False)
    fig.suptitle("Estimated savings from staging crews two hours ahead, 2025", x=0.02, ha="left", fontsize=14,
                 fontweight="bold")
    fig.text(0.02, -0.1, "Each dot is one scenario: a staged crew shortens outages by 10% or 25%; staging costs "
             "\\$5,000 or \\$20,000 per county per 6 hours. Typical customer mix; outage costs from Berkeley Lab's "
             "ICE models.\nThe model here is the version without HRRR forecasts.", color=MUTED, fontsize=9)
    fig.tight_layout()
    save(fig, "value.jpg")


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
    fig.suptitle(f"Trees and outages: linked in Missouri, not in Illinois (r = {r:.2f})", x=0.125, y=1.0, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(0.01, -0.02, "One dot per county. Storm hit rate: share of blocks with a NOAA storm report that had "
             "≥ 1% of customers out, 2020–2025.", color=MUTED, fontsize=8.5)
    save(fig, "canopy-scatter.jpg")


def canopy_effect():
    """Mean relative change in onset PR-AUC from adding canopy, pooled model scored per state, over seeds."""
    d = pd.read_csv(RESULTS / "canopy_by_state.csv").query("setup == 'pooled'")
    t = d.pivot_table(index=["state", "seed"], columns="features", values="onset_pr_auc")
    effect = (t["with canopy"] / t["without canopy"] - 1).groupby(level=0)
    return {state: {"mean": round(float(e.mean()), 3), "better": int((e > 0).sum()), "seeds": int(e.size)}
            for state, e in effect}


def story_data(gdf):
    """One JSON for the story page (site/index.html): county shapes (lon/lat, simplified), the March 2025 storm
    hour by hour, the heartbeat example, and the hourly results (ml/export_hourly.py)."""
    shapes = gpd.read_parquet(ROOT / "data" / "raw" / "geo" / "regions_study.parquet")
    # state outlines from the full-detail shapes: dissolving simplified counties leaves slivers
    # along shared borders, which then draw as stray lines
    outlines = shapes.dissolve("state").geometry.simplify(0.01, preserve_topology=True)
    shapes["geometry"] = shapes.geometry.simplify(0.01, preserve_topology=True)

    def rounded(geom):
        g = json.loads(gpd.GeoSeries([geom]).to_json())["features"][0]["geometry"]
        def walk(c):
            return [walk(x) for x in c] if isinstance(c[0], list) else [round(c[0], 3), round(c[1], 3)]
        g["coordinates"] = walk(g["coordinates"])
        return g

    order = shapes.region_fips.tolist()
    counties = [{"id": r.region_fips, "name": r.region, "state": r.state, "geometry": rounded(r.geometry)}
                for r in shapes.itertuples()]
    states = [{"name": name, "geometry": rounded(geom)} for name, geom in outlines.items()]
    meta = json.loads((APP / "meta_hourly.json").read_text())
    lead = meta["lead_hours"]

    con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
    heartbeat = con.sql("""
        SELECT block_start, n_snapshots FROM intermediate.int_eaglei__blocks_6h
        WHERE block_start BETWEEN '2024-05-21' AND '2024-05-27' ORDER BY 1
    """).df()
    n_hours = con.sql("SELECT count(*) FROM marts.mart_study__region_1h WHERE year(hour) BETWEEN 2020 AND 2025") \
        .fetchall()[0][0]
    hours = con.sql(f"""
        SELECT region_fips, hour, pct_out, pct_out * customers / 100 AS out FROM marts.mart_study__region_1h
        WHERE hour BETWEEN TIMESTAMP '{STORM_HOURS[0] - pd.Timedelta(hours=1)}'
                       AND TIMESTAMP '{STORM_HOURS[-1] + pd.Timedelta(hours=6)}'
    """).df()
    con.close()
    tests = subprocess.run(["dbt", "ls", "--resource-type", "test", "--quiet"], cwd=ROOT, capture_output=True,
                           text=True).stdout.split()

    # the storm, hour by hour: the risk decided LEAD hours before each hour t, for the 6 hours from t, beside
    # the worst share out in those 6 hours. Regions already >= 5% out at t - 1 have nothing to predict.
    ens = pd.read_parquet(ROOT / "data" / "cache" / "forecast_ensemble_2025.parquet")
    ens = ens[ens.block_start.between(STORM_HOURS[0] - pd.Timedelta(hours=lead),
                                      STORM_HOURS[-1] - pd.Timedelta(hours=lead))]
    pct = hours.pivot(index="hour", columns="region_fips", values="pct_out").reindex(columns=order)
    out = hours.pivot(index="hour", columns="region_fips", values="out").reindex(columns=order)
    storm = []
    for t in STORM_HOURS:
        e = ens[ens.block_start == t - pd.Timedelta(hours=lead)].set_index("region_fips").reindex(order)
        worst = pct.loc[t: t + pd.Timedelta(hours=5)].max()
        already = pct.loc[t - pd.Timedelta(hours=1)] >= THRESHOLD
        now = out.loc[t]
        r3 = lambda v: None if pd.isna(v) else round(float(v), 3)          # noqa: E731
        storm.append({
            "start": t.isoformat() + "Z",
            "prob": [r3(v) for v in e.p_mean], "low": [r3(v) for v in e.p_low], "high": [r3(v) for v in e.p_high],
            "pct": [None if pd.isna(v) else round(float(v), 1) for v in worst],
            "already": [bool(v) for v in already],
            "out_mo": int(now[now.index.str.startswith("29")].sum()),
            "out_il": int(now[now.index.str.startswith("17")].sum()),
        })

    def scores(name):
        d = pd.read_csv(RESULTS / f"benchmark_{name}.csv")
        d["split"] = d["split"].str.split("(").str[0]
        return d[(d.threshold_pct == 5) & (d.split == "time")]

    final = scores("final_2025")
    best = final[(final.model == "xgboost") & (final.features == "weather+place+recent")].iloc[0]

    ladder = pd.read_parquet(APP / "ladder.parquet")
    lead_time = pd.read_parquet(APP / "lead_time.parquet")
    # each line's key in text.yaml (lead.labels), and a fallback label
    runs = {"Warnings + outlook (rate table)": ("official", "Warnings + outlook alone"),
            "Model: weather + place + recent": ("weather", "Model, weather so far only"),
            "+ neighbours (final)": ("model", "Model + warnings + outlook")}
    at = meta["at_headline_share"]
    calib = pd.read_parquet(APP / "calibration.parquet")
    acc = pd.read_parquet(APP / "county_hourly.parquet").set_index("region_fips").reindex(order)
    canopy = gdf.set_index("region_fips").reindex(order)
    dollars = pd.read_csv(RESULTS / "value_hourly_2025.csv").query("mix == 'typical mix'")

    data = {
        "counties": counties, "states": states,
        "lead": lead, "storm": storm,
        "heartbeat": [{"start": r.block_start.isoformat() + "Z", "n": int(r.n_snapshots)}
                      for r in heartbeat.itertuples()],
        "pipeline": {"hours": int(n_hours), "counties": len(order), "tests": len(tests)},
        # trap 2 is measured on the first, 6-hour version: every block against new outages only
        "persistence": {"all": round(float(best.pr_auc), 3), "new": round(float(best.onset_pr_auc), 3)},
        "ladder": [{"label": LADDER_LABELS[r.model], "key": r.model, "value": round(float(r.onset_pr_auc), 3),
                    "lo": round(float(r.lo), 3), "hi": round(float(r.hi), 3),
                    "ratio": round(float(r.ratio_vs_official), 2), "ratio_lo": round(float(r.ratio_vs_official_lo), 2),
                    "ratio_hi": round(float(r.ratio_vs_official_hi), 2),
                    "better": round(float(getattr(r, "better_vs_official", float("nan"))), 3),
                    "ours": r.model == meta["headline_model"], "ceiling": "ceiling" in r.model}
                   for r in ladder.itertuples()],
        "lead_time": [{"key": key, "label": label,
                       "points": [{"lead": int(r.lead_hours), "value": round(float(r.onset_pr_auc), 3)}
                                  for r in lead_time[lead_time.run == run].itertuples()]}
                      for run, (key, label) in runs.items()],
        # paired storm-day permutation tests (ml/significance.py)
        "significance": {f"{r.challenger} vs {r.reference}": round(float(r.p_permutation), 3)
                         for r in pd.read_csv(RESULTS / "significance_2025.csv").itertuples()},
        "alerts": {"base_rate": round(meta["event_rate"], 4), "share": meta["headline_share"],
                   "new_outages": meta["n_new_outages"], "decisions": meta["n_decisions"],
                   **{k: {"caught": round(at[m]["caught"], 3), "precision": round(at[m]["precision"], 3),
                          "episodes": int(at[m]["episodes"])}
                      for k, m in (("model", meta["headline_model"]), ("newest", "With HRRR forecasts (newest run)"),
                                   ("official", "Warnings + outlook"), ("none", "No forecasts"))}},
        "calibration": [{"mean": round(float(r.mean_probability), 4), "observed": round(float(r.outage_share), 4),
                         "low": round(float(r.range_low), 4), "high": round(float(r.range_high), 4),
                         "n": int(r.decisions)} for r in calib.itertuples()],
        "accuracy": {"min_events": MIN_EVENTS,
                     "new": [int(v) for v in acc.new_outages.fillna(0)],
                     "caught": [int(v) for v in acc.caught.fillna(0)],
                     "expected": [round(float(v), 2) for v in acc.expected.fillna(0)]},
        "canopy": {"pct": [round(float(v), 1) for v in canopy.canopy_mean_pct],
                   "hit": [round(float(v), 4) for v in canopy.storm_hit_rate],
                   "r": {state: round(float(np.corrcoef(g.canopy_mean_pct, g.storm_hit_rate)[0, 1]), 2)
                         for state, g in canopy.groupby("state")} | {
                       "all": round(float(np.corrcoef(canopy.canopy_mean_pct, canopy.storm_hit_rate)[0, 1]), 2)},
                   # what knowing the canopy adds to the model, per state (ml/canopy_by_state.py: pooled model, 2024)
                   "model": canopy_effect()},
        "value": {
            "forecasts": [{"key": col, "label": label, "ours": col == "model",
                           "scenarios": [round(float(v) / 1e6, 1) for v in dollars[col]]}
                          for col, label in HOURLY_VALUE],
            "scenarios": [{"cut": float(r.restoration_cut), "cost": int(r.staging_cost)} for r in dollars.itertuples()],
        },
    }
    out = ROOT / "site" / "data" / "story.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, separators=(",", ":")))
    return out


class StormFrame:
    """The March 2025 storm on a 1200x630 canvas, hour by hour, from site/data/story.json: the risk decided two
    hours ahead beside the worst share out in the same 6 hours. Counties are drawn once; draw(k, t) only recolors
    them, so the clip can tween between hours. Regions already out when the window began are drawn gray."""

    def __init__(self, gdf, story):
        frames = story["storm"]
        self.lead = story["lead"]
        self.when = [pd.Timestamp(f["start"]) for f in frames]
        self.prob = np.array([[np.nan if v is None else v for v in f["prob"]] for f in frames], dtype=float)
        self.pct = np.array([[np.nan if v is None else v for v in f["pct"]] for f in frames], dtype=float)
        self.already = np.array([f["already"] for f in frames])
        self.out = [(f["out_mo"], f["out_il"]) for f in frames]
        self.vmax_p, self.vmax_o = 0.4, 25.0          # outages above 25% share the darkest color
        self.peak = int(np.nanargmax(np.nansum(self.prob, axis=1)))       # the hour with the most risk ahead

        self.fig = plt.figure(figsize=(6, 3.15), dpi=200)
        parts = gdf.reset_index(drop=True).explode(index_parts=False)     # one patch per polygon part
        self.part_of = parts.index.to_numpy()                             # part -> county row
        self.maps = []
        for left, title, colors, vmax, step, label, fmt in [
                (0.035, "Risk, decided 2 hours before", BLUE, self.vmax_p, 0.2, "chance of a new outage",
                 lambda v: f"{v:.0%}"),
                (0.52, "What happened in those 6 hours", ORANGE, self.vmax_o, 25, "worst share of customers out",
                 lambda v: f"{v:.0f}%" + ("+" if v >= 25 else ""))]:
            ax = self.fig.add_axes([left, 0.13, 0.30, 0.6])         # the map fills ~0.30 of the width
            parts.plot(ax=ax, facecolor=SURFACE, edgecolor=SURFACE, linewidth=0.3)
            gdf.dissolve("state").boundary.plot(ax=ax, color=INK_2, linewidth=0.6)
            minx, miny, maxx, maxy = gdf.total_bounds
            ax.set_xlim(minx, maxx)
            ax.set_ylim(miny, maxy)
            ax.set_aspect("equal", anchor="W")
            ax.set_axis_off()
            self.fig.text(left, 0.765, title, fontsize=9, fontweight="bold")
            cax = self.fig.add_axes([left + 0.315, 0.36, 0.12, 0.022])     # in the space right of the map
            ticks = np.arange(0, vmax + 1e-9, step)
            bar = colorbar(self.fig, cax, colors, 0, vmax, label, ticks, [fmt(t) for t in ticks])
            bar.ax.tick_params(labelsize=5.5, length=2)
            bar.ax.xaxis.label.set_fontsize(5.5)
            bar.ax.xaxis.set_label_position("top")
            self.maps.append((ax.collections[0], cmap(colors), plt.Normalize(0, vmax)))
        self.fig.text(0.035, 0.94, "Which counties will lose power in the next few hours?", fontsize=12.5,
                      fontweight="bold", va="top")
        self.subtitle = self.fig.text(0.035, 0.855, "", fontsize=7.5, color=INK_2, va="top")
        self.totals = self.fig.text(0.035, 0.085, "", fontsize=7, color=INK_2, va="top")
        self.fig.text(0.965, 0.085, "ugobruzadin.github.io/storm-outage-risk", fontsize=6.5, color=MUTED, ha="right",
                      va="top")

    def draw(self, k, t=0.0):
        """Hour k, blended a fraction t of the way toward hour k + 1."""
        nxt = min(k + 1, len(self.when) - 1)
        step = nxt if t >= 0.5 else k
        for (patches, ramp, norm), values in zip(self.maps, (self.prob, self.pct), strict=True):
            v = (1 - t) * values[k] + t * values[nxt]
            colors = ramp(norm(np.clip(np.nan_to_num(v), 0, norm.vmax)))
            colors[np.isnan(v)] = plt.matplotlib.colors.to_rgba("#e4e3dc")
            colors[self.already[step]] = plt.matplotlib.colors.to_rgba(HATCH)      # already out: not asked
            patches.set_facecolor(colors[self.part_of])
        ct = self.when[step].tz_convert("America/Chicago")
        decided = ct - pd.Timedelta(hours=self.lead)
        self.subtitle.set_text(f"{ct:%-d %B, %-I %p}–{ct + pd.Timedelta(hours=6):%-I %p} CT, as seen at "
                               f"{decided:%-I %p} from the forecasts available then. A storm it never trained on.")
        mo, il = self.out[step]
        self.totals.set_text(f"Customers out: Missouri {mo:,} · Illinois {il:,}  ·  Gray: already out")


def social_card(gdf, story):
    frame = StormFrame(gdf, story)
    frame.draw(frame.peak)
    frame.fig.savefig(OUT / "social.jpg", pil_kwargs={"quality": 90})      # no tight bbox: exactly 1200x630
    plt.close(frame.fig)


def storm_clip(gdf, story, fps=30, hold=0.45, tween=0.25):
    """MP4 (H.264, needs ffmpeg) for LinkedIn and Reddit: each hour held `hold` seconds, `tween` seconds of
    blending to the next, and the last hour held five times as long."""
    from matplotlib.animation import FFMpegWriter
    frame = StormFrame(gdf, story)
    n = len(frame.when)
    plan = []
    for k in range(n):
        plan += [(k, 0.0)] * int(fps * hold * (5 if k == n - 1 else 1))
        if k < n - 1:
            m = int(fps * tween)
            plan += [(k, (i + 1) / (m + 1)) for i in range(m)]
    writer = FFMpegWriter(fps=fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "23"])
    with writer.saving(frame.fig, str(OUT / "storm.mp4"), dpi=200):
        for k, t in plan:
            frame.draw(k, t)
            writer.grab_frame()
    plt.close(frame.fig)


if __name__ == "__main__":
    import sys
    gdf = load()
    if "--story" in sys.argv:                  # only the story page's data and the storm card and clip
        story = story_data(gdf)
        frames = json.loads(story.read_text())
        social_card(gdf, frames)
        storm_clip(gdf, frames)
        print(f"wrote {story.relative_to(ROOT)} ({story.stat().st_size / 1e3:.0f} kB), social.jpg, storm.mp4")
        sys.exit()
    accuracy(gdf)
    burden_map(gdf)
    results()
    canopy_map(gdf)
    canopy_scatter(gdf)
    value_figure()
    story = story_data(gdf)
    frames = json.loads(story.read_text())
    social_card(gdf, frames)
    storm_clip(gdf, frames)
    print(f"wrote {story.relative_to(ROOT)} ({story.stat().st_size / 1e3:.0f} kB),",
          ", ".join(p.name for p in sorted(OUT.glob("*.jpg"))))
