"""Shared helpers for the dashboard: data loading and chart styling.

Data: the app only reads the small Parquet files written by
`pixi run export-app`. Locally they're in data/app/; deployed, set
APP_DATA to the Hugging Face dataset, e.g.
    APP_DATA=hf://datasets/<user>/storm-outage-risk-data
DuckDB reads either path with the same SQL.

Style: colors come from one validated palette (sequential blue for "how
much", a second sequential hue — orange — when two magnitudes sit side by
side, fixed categorical order for series). Light and dark each get their own
steps; the dark ones are chosen for the dark surface, not inverted.
"""
import json
import os
from pathlib import Path

import duckdb
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
APP_DATA = os.environ.get("APP_DATA", str(ROOT / "data" / "app"))

LIGHT = {
    "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
    "grid": "#e1e0d9", "axis": "#c3c2b7", "map_style": "carto-positron",
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"],
}
DARK = {
    "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
    "grid": "#2c2c2a", "axis": "#383835", "map_style": "carto-darkmatter",
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500"],
}
# sequential ramps, light -> dark ("near zero" recedes toward the surface)
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORANGE = ["#fde0d2", "#f8b998", "#f2925f", "#eb6834", "#c84f1f", "#9c3c16", "#6e2a0f"]


def theme():
    """The palette matching Streamlit's current light/dark theme."""
    kind = getattr(getattr(st.context, "theme", None), "type", "light")
    return DARK if kind == "dark" else LIGHT


def ramp(colors):
    """A Plotly continuous colorscale from a list of ramp steps."""
    return [[i / (len(colors) - 1), c] for i, c in enumerate(colors)]


def style(fig, height=None):
    """Recessive chrome: hairline grid, muted axes, system sans, no chart junk."""
    t = theme()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=t["ink2"], size=13),
        margin=dict(l=8, r=8, t=36, b=8), hoverlabel=dict(font_size=13),
        # legend under the plot, so it never collides with the chart title
        legend=dict(orientation="h", yanchor="top", y=-0.15, x=0, title_text=""),
        **({"height": height} if height else {}),
    )
    fig.update_xaxes(gridcolor=t["grid"], linecolor=t["axis"], tickfont_color=t["muted"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], tickfont_color=t["muted"], zeroline=False)
    return fig


@st.cache_resource(show_spinner=False)
def connection():
    """One DuckDB connection; with HF_TOKEN set, it can read a private Hugging Face dataset."""
    con = duckdb.connect()
    if APP_DATA.startswith("hf://") and os.environ.get("HF_TOKEN"):
        con.execute("CREATE SECRET hf (TYPE huggingface, TOKEN ?)", [os.environ["HF_TOKEN"]])
    return con


@st.cache_data(show_spinner=False)
def table(name):
    """One exported table as a DataFrame (local path or hf://)."""
    return connection().sql(f"SELECT * FROM '{APP_DATA}/{name}.parquet'").df()


@st.cache_data(show_spinner=False)
def meta():
    return json.loads(_read_text("meta.json"))


@st.cache_data(show_spinner=False)
def meta_hourly():
    """What ml/export_hourly.py measured: the headline model, its alert level and the numbers the pages quote."""
    return json.loads(_read_text("meta_hourly.json"))


TEXT_FILE = Path(__file__).parent / "text.yaml"


class _KeepMissing(dict):
    def __missing__(self, key):                  # a placeholder with no value stays visible as {key}
        return "{" + key + "}"


@st.cache_data(show_spinner=False)
def _text(modified):                             # keyed on the file's modification time: edits show on rerun
    import yaml
    return yaml.safe_load(TEXT_FILE.read_text())


def text(key, **values):
    """The words at `key` in app/text.yaml (e.g. "storm_room.title"), with {placeholders} filled from values."""
    node = _text(TEXT_FILE.stat().st_mtime)
    for part in key.split("."):
        node = node[part]
    return node.format_map(_KeepMissing(values)) if isinstance(node, str) else node


def _read_text(name):
    path = f"{APP_DATA}/{name}"
    if path.startswith("hf://"):
        return connection().sql(f"SELECT content FROM read_text('{path}')").fetchall()[0][0]
    return Path(path).read_text()


@st.cache_data(show_spinner=False)
def geojson():
    """FeatureCollection of region shapes, keyed by region_fips (for choropleths)."""
    regions = table("regions")
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "id": r.region_fips, "geometry": json.loads(r.geojson)}
                     for r in regions.itertuples()],
    }


@st.cache_data(show_spinner=False)
def study_area():
    """How many counties, which states (alphabetical) and the map view that fits them, from the exported regions."""
    import math

    regions = table("regions")
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0])
            ys.append(c[1])
        else:
            for part in c:
                walk(part)

    for g in regions.geojson:
        walk(json.loads(g)["coordinates"])
    span = max(max(xs) - min(xs), 1.3 * (max(ys) - min(ys)))      # degrees; latitude stretched as on the map
    states = sorted(regions.state.unique())
    return {"counties": len(regions), "states": states,
            "where": states[0] if len(states) == 1 else ", ".join(states[:-1]) + " and " + states[-1],
            "center": {"lat": (min(ys) + max(ys)) / 2, "lon": (min(xs) + max(xs)) / 2},
            "zoom": math.log2(360 / span)}


def choropleth(df, value, label, colors=BLUE, range_color=None, hover=None, height=520, zoom=-0.6,
               legend="right"):
    """A county map of one magnitude, single-hue ramp. legend="bottom" frees the width for narrow columns.
    zoom: steps in or out from the view that just fits the study area (negative = out)."""
    area = study_area()
    import plotly.express as px

    fig = px.choropleth_map(
        df, geojson=geojson(), locations="region_fips", color=value,
        color_continuous_scale=ramp(colors), range_color=range_color,
        map_style=theme()["map_style"], opacity=0.85,
        center=area["center"], zoom=area["zoom"] + zoom,
        hover_name="region", hover_data=hover or {value: ":.2f", "region_fips": False},
        labels={value: label},
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color=theme()["surface"])
    if range_color and range_color[1] <= 1:                          # shares: label the color bar in percent
        fig.update_coloraxes(colorbar_tickformat=".0%")
    if legend == "bottom":
        bar = dict(title=dict(text=label, side="top"), orientation="h", thickness=10, len=0.7,
                   x=0.5, xanchor="center", y=-0.02, yanchor="top")
    else:
        bar = dict(title=label, thickness=10, len=0.6)
    fig.update_layout(coloraxis_colorbar=bar)
    return style(fig, height=height)


def gray_missing(fig, df, value, note):
    """Draw the counties with no `value` in neutral gray (not blank), with `note` in their tooltip."""
    import plotly.graph_objects as go

    missing = df[df[value].isna()]
    if len(missing):
        t = theme()
        fig.add_trace(go.Choroplethmap(
            geojson=geojson(), locations=missing.region_fips, z=[0] * len(missing),
            colorscale=[[0, t["axis"]], [1, t["axis"]]], showscale=False, marker_opacity=0.85,
            marker_line_width=0.5, marker_line_color=t["surface"], customdata=missing.region,
            hovertemplate="<b>%{customdata}</b><br>" + note + "<extra></extra>"))
    return fig


# --- page furniture, in the story page's style --------------------------------------------------------
LIVE_LATEST = "https://raw.githubusercontent.com/UgoBruzadin/storm-outage-live/main/latest.json"


def kicker(words):
    """The small uppercase line above a title, as on the story page."""
    st.markdown(f"<p style='font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;"
                f"color:{theme()['muted']};margin:0 0 -6px'>{words}</p>", unsafe_allow_html=True)


def stat_row(stats):
    """Big numbers with a line of explanation under each: [(value, explanation), ...]."""
    t = theme()
    cells = "".join(
        f"<div style='flex:1 1 220px;min-width:0'>"
        f"<div style='font-size:clamp(2.2rem,5vw,3.4rem);font-weight:800;line-height:1;color:{t['ink']};"
        f"font-variant-numeric:tabular-nums'>{value}</div>"
        f"<div style='margin-top:8px;font-size:.95rem;line-height:1.4;color:{t['ink2']}'>{about}</div></div>"
        for value, about in stats)
    st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:24px 40px;margin:18px 0 26px;padding:22px 0;"
                f"border-top:1px solid {t['grid']};border-bottom:1px solid {t['grid']}'>{cells}</div>",
                unsafe_allow_html=True)


@st.cache_data(ttl=600, show_spinner=False)
def live_latest():
    """The newest live forecast (storm-outage-live), or None if GitHub can't be reached."""
    import urllib.request
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        with urllib.request.urlopen(LIVE_LATEST, timeout=10) as r:
            d = json.load(r)
    except (OSError, ValueError):
        return None
    hour = datetime.fromisoformat(d["decision_hour"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Chicago"))
    d["when"] = hour.strftime("%a %-d %b, %-I %p CT")
    return d
