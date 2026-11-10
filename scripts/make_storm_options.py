"""Five candidate storm animations, to compare side by side. Everything uses the scored model (new outages only), so a
county with an outage in the past day has no score and shows black: "already hit".

  1 three-maps          official forecasts, the model, what happened (wide and 4:5)
  2 two-storms          the same, 14 March and then 5 January, when winter warnings did well
  3 forecast-radar      HRRR's simulated radar, the model, what happened
  4 one-map             everything in layers on one map, for phones
  5 countdown           one map: the risk arrives, then the outage follows

Writes data/cache/storm_options/ (not site/assets: nothing here is published until one is chosen).
Usage: pixi run python scripts/make_storm_options.py [--stills]
"""
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))      # run as a script: make `ml` importable

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from make_site_figures import BLUE, INK, INK_2, MUTED, ORANGE, ROOT, SURFACE, cmap, load
from matplotlib.animation import FFMpegWriter
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch, Rectangle

from ml.export_hourly import HEADLINE_SHARE, predictions

OUT = ROOT / "data" / "cache" / "storm_options"
LEAD, FPS, HOLD, TWEEN = 2, 30, 0.45, 0.25
MARCH = pd.date_range("2025-03-14 18:00", periods=28, freq="h")
JANUARY = pd.date_range("2025-01-05 04:00", periods=22, freq="h")
VMAX_P, VMAX_O, VMAX_R = 0.4, 25.0, 60.0
HIT = "#111111"                                                      # no score: an outage in the past day
RISK = BLUE[:6]                                                      # stops short of black, which means HIT
OUTLOOK = ["#f4f3ee", "#e6e5de", "#d6d5cd", "#c4c3ba", "#b1b0a6", "#9d9c92"]
WARNING = "#6b3fa0"
RADAR = ["#f1f0ea", "#c9d8c3", "#8fb48a", "#5b8d5c", "#2f6238", "#143d1f"]
URL = "ugobruzadin.github.io/storm-outage-risk"
ALREADY_HIT = "Already hit: the model only forecasts new outages"
SUMMARY = {
    "march": "14 March, all day: 94 new outages. Warnings were in force 2+ hours ahead for 19. "
             "The model caught 90 with 1,132 county-hours of alerts; warnings + outlook's riskiest hours caught 93 "
             "with 3,480. About 85% of the model's alerts all year had no outage.",
    "january": "5 January, all day: 42 new outages. Winter warnings were in force 2+ hours ahead for 40. "
               "The model caught 38. Warnings are built for short lead times; on winter storms they can do very well.",
}


class Storm:
    """One storm's frames: for window start t (decision t - LEAD), per county, every layer an animation can draw."""

    def __init__(self, hours, fips, level, scored):
        self.hours, self.fips = hours, fips
        n, m = len(hours), len(fips)
        where = {f: i for i, f in enumerate(fips)}
        self.prob = np.full((n, m), np.nan)
        rows = scored[scored.block_start.isin(hours - pd.Timedelta(hours=LEAD))]
        steps = {t: i for i, t in enumerate(hours - pd.Timedelta(hours=LEAD))}
        for r in rows.itertuples():
            self.prob[steps[r.block_start], where[r.region_fips]] = r.p_mean
        self.alert = self.prob >= level
        con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
        start, end = hours[0] - pd.Timedelta(hours=LEAD), hours[-1] + pd.Timedelta(hours=6)
        h = con.sql(f"""SELECT region_fips, hour, pct_out, pct_out * customers / 100 AS out, spc_cat,
                               greatest(warn_svr, warn_tor, warn_wind, warn_winter) AS warned
                        FROM marts.mart_study__region_1h WHERE hour BETWEEN TIMESTAMP '{start}' AND TIMESTAMP '{end}'
                     """).df()
        con.close()
        self.out_now = np.zeros((n, m))
        self.worst = np.zeros((n, m))
        self.warned, self.outlook = np.zeros((n, m)), np.zeros((n, m))
        self.customers = np.zeros(n)
        pct = h.pivot(index="hour", columns="region_fips", values="pct_out").reindex(columns=fips)
        warned = h.pivot(index="hour", columns="region_fips", values="warned").reindex(columns=fips).fillna(0)
        spc = h.pivot(index="hour", columns="region_fips", values="spc_cat").reindex(columns=fips).fillna(0)
        total = h.groupby("hour").out.sum()
        for i, t in enumerate(hours):
            window = pct.loc[t:t + pd.Timedelta(hours=5)]
            self.worst[i] = window.max().fillna(0).to_numpy()
            self.out_now[i] = pct.loc[t].fillna(0).to_numpy() if t in pct.index else 0
            d = t - pd.Timedelta(hours=LEAD)
            self.warned[i], self.outlook[i] = warned.loc[d].to_numpy(), spc.loc[d].to_numpy()
            self.customers[i] = total.loc[t:t + pd.Timedelta(hours=5)].max()

    def radar(self):
        """Strongest simulated radar echo per county at the window's first hour, from the newest run at the decision."""
        days = sorted({(t - pd.Timedelta(hours=LEAD * 2)).date() for t in self.hours})
        f = pd.concat([pd.read_parquet(ROOT / "data" / "raw" / "weather" / "hrrr_fcst_area" / f"{d:%Y%m%d}.parquet",
                                       columns=["run", "fhour", "region_fips", "area_refc_max"]) for d in days])
        f = f[f.fhour == LEAD * 2]
        best = f.groupby(["run", "region_fips"]).area_refc_max.max().unstack().reindex(columns=self.fips)
        return np.stack([best.loc[t - pd.Timedelta(hours=LEAD * 2)].fillna(0).to_numpy() for t in self.hours])


def ramp_colors(values, colors, vmax, missing=HIT):
    rgba = cmap(colors)(np.clip(np.nan_to_num(values), 0, vmax) / vmax)
    rgba[np.isnan(values)] = to_rgba(missing)
    return rgba


def official_colors(s):
    rgba = cmap(OUTLOOK)(np.clip(s.outlook, 0, 6) / 6)
    rgba[s.warned > 0] = to_rgba(WARNING)
    return rgba


def base_map(fig, box, gdf, parts, edge=SURFACE):
    ax = fig.add_axes(box)
    parts.plot(ax=ax, facecolor=SURFACE, edgecolor=edge, linewidth=0.25)
    gdf.dissolve("state").boundary.plot(ax=ax, color=INK_2, linewidth=0.5)
    minx, miny, maxx, maxy = gdf.total_bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal", anchor="C")
    ax.set_axis_off()
    return ax


def ramp_key(fig, box, colors, low, high, label):
    ax = fig.add_axes(box)
    ax.imshow(np.linspace(0, 1, 128)[None, :], aspect="auto", cmap=cmap(colors))
    ax.set_axis_off()
    fig.text(box[0], box[1] + box[3] + 0.006, label, fontsize=5.8, color=INK_2, va="bottom")
    fig.text(box[0], box[1] - 0.006, low, fontsize=5.5, color=MUTED, va="top")
    fig.text(box[0] + box[2], box[1] - 0.006, high, fontsize=5.5, color=MUTED, va="top", ha="right")


def time_text(t):
    ct = t.tz_localize("UTC").tz_convert("America/Chicago")
    decided = ct - pd.Timedelta(hours=LEAD)
    return f"{ct:%-d %B, %-I %p}–{ct + pd.Timedelta(hours=6):%-I %p} CT, as seen at {decided:%-I %p}"


class Panels:
    """Maps side by side (or stacked), each a frames x counties x RGBA array, blended between hours."""

    def __init__(self, gdf, title, panels, layout):
        self.fig = plt.figure(figsize={"wide": (6, 3.15), "tall": (5.4, 6.75)}[layout], dpi=200)
        parts = gdf.reset_index(drop=True).explode(index_parts=False)
        self.part_of = parts.index.to_numpy()
        self.layers = []
        self.fig.text(0.03, 0.97, title, fontsize=11.5 if layout == "wide" else 12.5, fontweight="bold", va="top")
        self.when = self.fig.text(0.03, 0.912 if layout == "wide" else 0.935, "", fontsize=7, color=INK_2, va="top")
        self.total = self.fig.text(0.03, 0.135 if layout == "wide" else 0.08, "", fontsize=7, color=INK, va="top")
        self.width = 118 if layout == "wide" else 104
        self.note = self.fig.text(0.03, 0.135 if layout == "wide" else 0.088, "", fontsize=6.3, color=INK, va="top",
                                  linespacing=1.3)
        self.fig.text(0.97, 0.018, URL, fontsize=5.5, color=MUTED, ha="right", va="bottom")
        for i, (name, key) in enumerate(panels):
            if layout == "wide":
                box = (0.015 + i * 0.325, 0.285, 0.32, 0.53)
                head = (0.03 + i * 0.325, 0.822)
                bar = (0.03 + i * 0.325, 0.215, 0.20, 0.016)
            else:
                box = (0.03, 0.655 - i * 0.28, 0.60, 0.26)
                head = (0.645, 0.86 - i * 0.28)
                bar = (0.645, 0.78 - i * 0.28, 0.24, 0.012)
            ax = base_map(self.fig, box, gdf, parts)
            self.fig.text(*head, name, fontsize=8, fontweight="bold", va="bottom")
            key(self.fig, bar)
            self.layers.append(ax.collections[0])

    def draw(self, colors, k, t=0.0):
        nxt = min(k + 1, len(colors[0]) - 1)
        for patches, c in zip(self.layers, colors, strict=True):
            patches.set_facecolor(((1 - t) * c[k] + t * c[nxt])[self.part_of])


def official_key(fig, bar):
    ramp_key(fig, bar, OUTLOOK, "low", "high", "SPC outlook risk")
    fig.add_artist(Rectangle((bar[0] + bar[2] + 0.012, bar[1]), 0.014, bar[3], transform=fig.transFigure,
                             facecolor=WARNING, linewidth=0))
    fig.text(bar[0] + bar[2] + 0.012, bar[1] + bar[3] + 0.006, "warning", fontsize=5.8, color=INK_2, va="bottom")


def risk_key(fig, bar):
    ramp_key(fig, bar, RISK, "0%", "40%+", "chance of a new outage")
    tall = fig.get_figheight() > 5
    y = bar[1] - (0.05 if tall else 0.06)
    fig.add_artist(Rectangle((bar[0], y), 0.014, bar[3], transform=fig.transFigure, facecolor=HIT, linewidth=0))
    label = ALREADY_HIT.replace(": ", ":\n") if tall else ALREADY_HIT
    fig.text(bar[0] + 0.02, y + bar[3] / 2, label, fontsize=5.8, color=INK_2, va="center")


def out_key(fig, bar):
    ramp_key(fig, bar, ORANGE, "0%", "25%+", "worst share of customers out")


def radar_key(fig, bar):
    ramp_key(fig, bar, RADAR, "none", "60+ dBZ", "simulated radar for this hour")


def plan_frames(n):
    plan = []
    for k in range(n):
        plan += [(k, 0.0)] * int(FPS * HOLD)
        if k < n - 1:
            m = int(FPS * TWEEN)
            plan += [(k, (i + 1) / (m + 1)) for i in range(m)]
    return plan


def three_maps(gdf, storms, name, title, first, first_key, layout, stills):
    """storms: [(key, Storm)]. first: Storm -> the left panel's colors."""
    p = Panels(gdf, title, [(first[0], first_key), ("The model, 2 hours before", risk_key),
                            ("What happened", out_key)], layout)
    writer = FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "24"])
    prepared = [(key, s, [first[1](s), ramp_colors(s.prob, RISK, VMAX_P), ramp_colors(s.worst, ORANGE, VMAX_O)])
                for key, s in storms]

    def frame(s, colors, k, t):
        p.draw(colors, k, t)
        step = k + 1 if t >= 0.5 else k
        p.when.set_text(time_text(s.hours[step]))
        p.total.set_text(f"Customers out: {s.customers[step]:,.0f}")
        p.note.set_text("")

    def ending(key):
        p.total.set_text("")
        p.note.set_text(textwrap.fill(SUMMARY[key], p.width))

    if stills:
        key, s, colors = prepared[0]
        k = int(np.nanargmax(np.nansum(s.prob, axis=1)))
        frame(s, colors, k, 0)
        p.fig.savefig(OUT / f"{name}.png")
        ending(key)
        p.fig.savefig(OUT / f"{name}_end.png")
    else:
        with writer.saving(p.fig, str(OUT / f"{name}.mp4"), dpi=200):
            for key, s, colors in prepared:
                for k, t in plan_frames(len(s.hours)):
                    frame(s, colors, k, t)
                    writer.grab_frame()
                ending(key)
                for _ in range(FPS * 4):
                    writer.grab_frame()
    plt.close(p.fig)


def single_map(gdf, title, sub):
    fig = plt.figure(figsize=(5.4, 5.4), dpi=200)
    parts = gdf.reset_index(drop=True).explode(index_parts=False)
    ax = base_map(fig, (0.04, 0.17, 0.92, 0.66), gdf, parts)
    fig.text(0.04, 0.965, title, fontsize=14, fontweight="bold", va="top")
    fig.text(0.04, 0.905, sub, fontsize=7.5, color=INK_2, va="top")
    when = fig.text(0.04, 0.865, "", fontsize=8.5, fontweight="bold", color=INK, va="top")
    fig.text(0.96, 0.018, URL, fontsize=6, color=MUTED, ha="right", va="bottom")
    return fig, ax, when, parts.index.to_numpy()


def overlay(ax, gdf, **style):
    return gdf.boundary.plot(ax=ax, zorder=4, **style).collections[-1]


def one_map(gdf, s, name, stills):
    fig, ax, when, part_of = single_map(gdf, "One storm, three signals",
                                        "14–15 March 2025, as seen 2 hours before each 6-hour window")
    fills = ax.collections[0]
    alert = overlay(ax, gdf, color="none", linewidth=1.0)
    warn = overlay(ax, gdf, color="none", linewidth=0.9, linestyle=(0, (2, 1.4)))
    colors = ramp_colors(s.worst, ORANGE, VMAX_O, SURFACE)
    colors[s.worst < 1] = to_rgba(SURFACE)
    fig.legend(handles=[Patch(facecolor=ORANGE[3], label="Customers out"),
                        Patch(facecolor="none", edgecolor=BLUE[5], linewidth=1.3, label="Model alert"),
                        Patch(facecolor="none", edgecolor=WARNING, linewidth=0.9, linestyle="--",
                              label="Warning in force")],
               loc="lower left", bbox_to_anchor=(0.03, 0.08), ncol=3, frameon=False, fontsize=7.5)
    total = fig.text(0.04, 0.075, "", fontsize=7.5, color=INK, va="top")

    def draw(k, t=0.0):
        nxt = min(k + 1, len(s.hours) - 1)
        fills.set_facecolor(((1 - t) * colors[k] + t * colors[nxt])[part_of])
        step = nxt if t >= 0.5 else k
        alert.set_edgecolor([to_rgba(BLUE[5], float(v)) for v in s.alert[step]])
        warn.set_edgecolor([to_rgba(WARNING, float(v > 0)) for v in s.warned[step]])
        when.set_text(time_text(s.hours[step]))
        total.set_text(f"Customers out: {s.customers[step]:,.0f}")

    finish(fig, name, len(s.hours), draw, stills)


def countdown(gdf, s, name, stills):
    fig, ax, when, part_of = single_map(gdf, "The risk arrives. Then the outage.",
                                        "14–15 March 2025. Blue: the model expects a new outage in the next 2–8 hours.")
    fills = ax.collections[0]
    # at clock hour T: the outages now, and the risk decided at T (the row for the window starting T + LEAD)
    risk = ramp_colors(s.prob[LEAD:], RISK, VMAX_P)
    out_now = s.out_now[:-LEAD]
    now = cmap(ORANGE)(np.clip(out_now, 0, VMAX_O) / VMAX_O)
    colors = risk.copy()
    colors[out_now >= 5] = now[out_now >= 5]
    fig.legend(handles=[Patch(facecolor=BLUE[3], label="Risk ahead, seen now"),
                        Patch(facecolor=ORANGE[3], label="5%+ of customers out now"),
                        Patch(facecolor=HIT, label=ALREADY_HIT)],
               loc="lower left", bbox_to_anchor=(0.03, 0.08), ncol=2, frameon=False, fontsize=7.5)
    total = fig.text(0.04, 0.075, "", fontsize=7.5, color=INK, va="top")

    def draw(k, t=0.0):
        nxt = min(k + 1, len(colors) - 1)
        fills.set_facecolor(((1 - t) * colors[k] + t * colors[nxt])[part_of])
        step = nxt if t >= 0.5 else k
        ct = s.hours[step].tz_localize("UTC").tz_convert("America/Chicago")
        when.set_text(f"{ct:%-d %B, %-I %p} CT")
        total.set_text(f"Counties 5%+ out now: {int((out_now[step] >= 5).sum())}")
    finish(fig, name, len(colors), draw, stills)


def finish(fig, name, n, draw, stills):
    if stills:
        draw(n // 3)
        fig.savefig(OUT / f"{name}.png")
    else:
        writer = FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "24"])
        with writer.saving(fig, str(OUT / f"{name}.mp4"), dpi=200):
            for k, t in plan_frames(n):
                draw(k, t)
                writer.grab_frame()
            for _ in range(FPS * 3):
                writer.grab_frame()
    plt.close(fig)


if __name__ == "__main__":
    stills = "--stills" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    gdf = load()
    fips = gdf.region_fips.to_numpy()
    pred = predictions()
    level = float(np.quantile(pred.p_mean, 1 - HEADLINE_SHARE))
    scored = pred[["region_fips", "block_start", "p_mean"]]
    march, january = Storm(MARCH, fips, level, scored), Storm(JANUARY, fips, level, scored)
    official = ("Official forecasts, 2 hours before", official_colors)
    title = "The same storm, as each forecast saw it two hours earlier"
    three_maps(gdf, [("march", march)], "1-three-maps-wide", title, official, official_key, "wide", stills)
    three_maps(gdf, [("march", march)], "1-three-maps-tall", title, official, official_key, "tall", stills)
    three_maps(gdf, [("march", march), ("january", january)], "2-two-storms", title, official, official_key, "wide",
               stills)
    radar = march.radar()
    three_maps(gdf, [("march", march)], "3-forecast-radar", "The storm the forecast drew, and who it would hit",
               ("Forecast radar, 2 hours before", lambda s: ramp_colors(radar, RADAR, VMAX_R)), radar_key, "wide",
               stills)
    one_map(gdf, march, "4-one-map", stills)
    countdown(gdf, march, "5-countdown", stills)
