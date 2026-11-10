"""All of 2025 as an animation, for the portfolio card and social posts: the same new outages on two maps, in color
where that forecast alerted in time and in gray where it didn't. Unlike the story page's storm replay, this uses the
scored models and every day of the year, so no storm is picked.

Each forecast alerts on its own riskiest 0.75% of county-hours, as on the pages. Counties tint while on alert.

Writes site/assets/:
  year-2025.mp4         1200x630, for the portfolio card
  year-2025-square.mp4  1080x1080, for LinkedIn and Reddit
  social.jpg            1200x630 link-preview card: the clip's last frame

Usage: pixi run python scripts/make_year_clip.py [--stills]   (needs the warehouse, data/cache and ffmpeg)
--stills writes a few frames to data/cache/clip_stills/ instead of the clips.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))      # run as a script: make `ml` importable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from make_site_figures import BLUE, INK, INK_2, LINE, MUTED, OUT, ROOT, SURFACE, load
from matplotlib.animation import FFMpegWriter
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from ml.export_hourly import HEADLINE_SHARE, predictions
from ml.moving_window import caught_flags, onset_hours
from ml.uncertainty import storm_day

LEAD, FPS = 2, 30
MODEL, OFFICIAL = "p_mean", "warnings + outlook"
CAUGHT, MISSED, TINT = BLUE[4], "#b5b4ac", BLUE[0]
LOUD_DAY = 10                    # a day with this many new outages keeps its line on screen until the next one
END_HOLD_S = 5
URL = "ugobruzadin.github.io/storm-outage-risk"
LAYOUTS = {
    "wide": {"size": (6, 3.15), "maps": [(0.03, 0.20, 0.30, 0.58), (0.51, 0.20, 0.30, 0.58)], "title": 12, "big": 21,
             "head_y": 0.815, "count_dx": 0.305, "count_y": 0.60, "strip": (0.03, 0.055, 0.60, 0.075), "read_y": 0.165,
             "url": (0.97, 0.875), "end_y": 0.135, "end_size": 6.8, "dot": 1.5},
    "square": {"size": (5.4, 5.4), "maps": [(0.03, 0.27, 0.45, 0.45), (0.52, 0.27, 0.45, 0.45)], "title": 13, "big": 25,
               "head_y": 0.845, "count_dx": 0.0, "count_y": 0.74, "strip": (0.05, 0.075, 0.90, 0.085), "read_y": 0.215,
               "url": (0.95, 0.025), "end_y": 0.215, "end_size": 7.6, "dot": 2.2},
}


def year_data():
    """Per new outage: its county, storm day and whether each forecast caught it; per storm day and county: on alert."""
    pred = predictions()
    onsets = onset_hours(2025)
    on = onsets.assign(day=storm_day(onsets.hour))
    alerts = {}
    for col in (MODEL, OFFICIAL):
        flagged = pd.Series(pred[col].to_numpy() > np.quantile(pred[col], 1 - HEADLINE_SHARE), index=pred.index)
        on[col] = caught_flags(pred, flagged, onsets, LEAD)
        hit = pred.loc[flagged, ["region_fips", "block_start"]]
        alerts[col] = set(zip(hit.region_fips, storm_day(hit.block_start), strict=True))
    # the numbers the pages quote
    assert (len(on), on[MODEL].sum(), on[OFFICIAL].sum()) == (1436, 429, 243)
    return on.sort_values("hour").reset_index(drop=True), alerts


def dot_positions(gdf, on):
    """One spot per new outage: a sunflower spiral from a point inside its county, so a county's dots don't overlap."""
    centers = gdf.set_index("region_fips").geometry.representative_point()
    xy, seen = np.zeros((len(on), 2)), {}
    for i, fips in enumerate(on.region_fips):
        k = seen.get(fips, 0)
        seen[fips] = k + 1
        r, angle = 4800 * np.sqrt(k), k * 2.39996
        xy[i] = centers[fips].x + r * np.cos(angle), centers[fips].y + r * np.sin(angle)
    return xy


def schedule(days, on):
    """Frames per day: one for a quiet day, more the more new outages, and a pause on the five biggest."""
    n = on.groupby("day").size().reindex(days, fill_value=0)
    frames = (1 + (n * 0.18).round()).astype(int)
    frames[n.nlargest(5).index] += 18
    return np.repeat(np.arange(len(days)), frames.to_numpy())


class YearClip:
    def __init__(self, gdf, on, alerts, layout):
        self.l, self.on = LAYOUTS[layout], on
        self.days = pd.date_range(storm_day(pd.Series([pd.Timestamp("2025-01-01")]))[0], on.day.max(), freq="D")
        self.day_of = np.searchsorted(self.days, on.day)
        self.fips = gdf.region_fips.to_numpy()
        self.columns = (MODEL, OFFICIAL)
        self.on_alert = {c: np.array([[(f, d) in alerts[c] for f in self.fips] for d in self.days])
                         for c in self.columns}
        self.tint = {c: np.zeros(len(self.fips)) for c in self.columns}
        self.base = np.array(to_rgb(SURFACE))
        self.alert = np.array(to_rgb(TINT))
        self.fig = plt.figure(figsize=self.l["size"], dpi=200)
        self.fig.text(0.03, 0.965, "Which new power outages did each forecast see coming?", fontsize=self.l["title"],
                      fontweight="bold", va="top")
        self.fig.text(0.03, 0.895 if layout == "wide" else 0.915,
                      "Every day of 2025, 2 hours ahead. Each alerts on its riskiest 0.75% of county-hours.",
                      fontsize=self.l["title"] * 0.62, color=INK_2, va="top")
        parts = gdf.reset_index(drop=True).explode(index_parts=False)
        self.part_of = parts.index.to_numpy()
        xy = dot_positions(gdf, on)
        self.panels = {}
        names = ("The model", "Official warnings + outlook")
        for box, col, name in zip(self.l["maps"], self.columns, names, strict=True):
            ax = self.fig.add_axes(box)
            parts.plot(ax=ax, facecolor=SURFACE, edgecolor=LINE, linewidth=0.25)
            gdf.dissolve("state").boundary.plot(ax=ax, color=MUTED, linewidth=0.5)
            minx, miny, maxx, maxy = gdf.total_bounds
            ax.set_xlim(minx, maxx)
            ax.set_ylim(miny, maxy)
            ax.set_aspect("equal", anchor="W")
            ax.set_axis_off()
            dots = ax.scatter(xy[:, 0], xy[:, 1], s=0, linewidths=0, zorder=3,
                              c=[CAUGHT if v else MISSED for v in on[col]])
            order = np.argsort(on[col].to_numpy())               # caught dots on top of missed ones
            dots.set_offsets(xy[order])
            dots.set_color([CAUGHT if v else MISSED for v in on[col].to_numpy()[order]])
            self.fig.text(box[0], self.l["head_y"], name, fontsize=8.5, fontweight="bold", va="center")
            x, y = box[0] + self.l["count_dx"], self.l["count_y"]
            big = self.fig.text(x, y, "0", fontsize=self.l["big"], fontweight="bold", color=CAUGHT, va="bottom")
            small = self.fig.text(x, y - 0.012, f"of {len(on):,} new\noutages caught", fontsize=6.5, color=INK_2,
                                  va="top")
            if layout == "square":
                big.set_position((box[0], 0.74))
                small.set_text(f"of {len(on):,} new outages caught")
                small.set_position((box[0] + 0.115, 0.752))
                small.set_va("bottom")
            self.panels[col] = {"patches": ax.collections[0], "dots": dots, "order": order, "big": big}
        self.reading = self.fig.text(0.03, self.l["read_y"], "", fontsize=7.2, color=INK, va="center")
        self.ending = self.fig.text(0.03, self.l["end_y"], "", fontsize=self.l["end_size"], color=INK, va="top",
                                    linespacing=1.35)
        self.fig.text(*self.l["url"], URL, fontsize=6, color=MUTED, ha="right", va="bottom")
        self.strip = self.fig.add_axes(self.l["strip"])
        per_day = on.groupby("day").size().reindex(self.days, fill_value=0).to_numpy()
        self.strip.bar(np.arange(len(self.days)), np.sqrt(per_day), width=1.0, color=INK_2, linewidth=0)
        self.strip.set_xlim(0, len(self.days))
        self.strip.set_yticks([])
        starts = [i for i, d in enumerate(self.days) if d.day == 1]
        self.strip.set_xticks(starts, [self.days[i].strftime("%b") for i in starts], fontsize=5.5)
        self.strip.tick_params(axis="x", length=0, pad=1.5, colors=MUTED)
        for side in ("top", "left", "right"):
            self.strip.spines[side].set_visible(False)
        self.future = self.strip.add_patch(Rectangle((0, 0), len(self.days), np.sqrt(per_day.max()), color=SURFACE,
                                                     alpha=0.8, zorder=3, linewidth=0))
        self.totals_by_day = on.groupby(self.day_of).size()

    def draw(self, d, grow=1.0):
        """Everything up to day d; today's dots are drawn larger and settle as `grow` runs from 0 to 1."""
        for col in self.columns:
            p = self.panels[col]
            self.tint[col] = np.maximum(self.tint[col] * 0.8, self.on_alert[col][d].astype(float))
            colors = self.base + self.tint[col][:, None] * (self.alert - self.base)
            p["patches"].set_facecolor(colors[self.part_of])
            sizes = np.where(self.day_of <= d, self.l["dot"], 0.0)
            sizes = np.where(self.day_of == d, self.l["dot"] * (1 + 4 * (1 - grow)), sizes)
            p["dots"].set_sizes(sizes[p["order"]])
            p["big"].set_text(f"{int(self.on[col][self.day_of <= d].sum()):,}")
        self.future.set_x(d + 1)
        loud = [k for k in self.totals_by_day.index if k <= d and self.totals_by_day[k] >= LOUD_DAY]
        if loud:
            k = loud[-1]
            self.reading.set_text(f"{self.days[k]:%-d %B}: {self.totals_by_day[k]} new outages")

    def end(self):
        """The last frame: the honest summary replaces the timeline."""
        self.strip.set_visible(False)
        self.reading.set_text("")
        for p in self.panels.values():
            p["patches"].set_facecolor(self.base)
        self.ending.set_text("Blue: caught at least 2 hours ahead. Gray: no alert in time. About 85% of the model's "
                             "alerts\nweren't followed by a new outage, and about 70% of outages got no alert. "
                             "Trained on 2020–2024.")


def clip(gdf, on, alerts, layout, name):
    c = YearClip(gdf, on, alerts, layout)
    plan = schedule(c.days, on)
    writer = FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "24"])
    with writer.saving(c.fig, str(OUT / name), dpi=200):
        for i, d in enumerate(plan):
            left = np.sum(plan == d)
            done = i - np.argmax(plan == d)
            c.draw(d, 1.0 if left == 1 else done / (left - 1))
            writer.grab_frame()
        c.draw(plan[-1])
        c.end()
        for _ in range(FPS * END_HOLD_S):
            writer.grab_frame()
    print(name, f"{(len(plan) + FPS * END_HOLD_S) / FPS:.0f} s", f"{(OUT / name).stat().st_size / 1e6:.1f} MB")
    plt.close(c.fig)


if __name__ == "__main__":
    gdf = load()
    on, alerts = year_data()
    if "--stills" in sys.argv:
        out = ROOT / "data" / "cache" / "clip_stills"
        out.mkdir(exist_ok=True)
        for layout in LAYOUTS:
            c = YearClip(gdf, on, alerts, layout)
            k = int(np.searchsorted(c.days, pd.Timestamp("2025-03-14")))
            c.draw(k, 0.4)
            c.fig.savefig(out / f"{layout}_march.png")
            c.draw(len(c.days) - 1)
            c.end()
            c.fig.savefig(out / f"{layout}_end.png")
            plt.close(c.fig)
        sys.exit()
    clip(gdf, on, alerts, "wide", "year-2025.mp4")
    clip(gdf, on, alerts, "square", "year-2025-square.mp4")
    c = YearClip(gdf, on, alerts, "wide")
    c.draw(len(c.days) - 1)
    c.end()
    c.fig.savefig(OUT / "social.jpg", pil_kwargs={"quality": 90})
