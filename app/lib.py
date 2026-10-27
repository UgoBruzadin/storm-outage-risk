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


def _read_text(name):
    path = f"{APP_DATA}/{name}"
    if path.startswith("hf://"):
        return connection().sql(f"SELECT content FROM read_text('{path}')").fetchall()[0][0]
    return Path(path).read_text()


@st.cache_data(show_spinner=False)
def shapes():
    """County and state shapes for the D3 components: coordinates rounded to ~100 m."""
    def rounded(coords):
        if isinstance(coords[0], list):
            return [rounded(c) for c in coords]
        return [round(coords[0], 3), round(coords[1], 3)]

    counties = []
    for r in table("regions").itertuples():
        geometry = json.loads(r.geojson)
        geometry["coordinates"] = rounded(geometry["coordinates"])
        counties.append({"id": r.region_fips, "name": r.region, "state": r.state, "geometry": geometry})
    return {"counties": counties, "states": json.loads(_read_text("states.json"))}


def shapes_order():
    """Region ids in the order the D3 components expect values."""
    return [c["id"] for c in shapes()["counties"]]


def d3_component(name, payload, height):
    """Render app/components/<name>.html (D3, shared base.js and style.css) with `payload` as DATA."""
    import streamlit.components.v1 as components

    folder = Path(__file__).parent / "components"
    markup = (folder / f"{name}.html").read_text()
    data = json.dumps({**shapes(), **payload}, separators=(",", ":"))
    head = ('<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>\n'
            f"<script>const DATA = {data};\nconst THEME = {json.dumps('dark' if theme() is DARK else 'light')};\n"
            f"{(folder / 'base.js').read_text()}</script>\n")
    html = (f"<!doctype html><html><head><meta charset='utf-8'><style>{(folder / 'style.css').read_text()}</style>"
            f"</head><body><div class='tip'></div>{markup.replace('<script>', head + '<script>', 1)}</body></html>")
    components.html(html, height=height)


@st.cache_data(show_spinner=False)
def geojson():
    """FeatureCollection of region shapes, keyed by region_fips (for choropleths)."""
    regions = table("regions")
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "id": r.region_fips, "geometry": json.loads(r.geojson)}
                     for r in regions.itertuples()],
    }


def choropleth(df, value, label, colors=BLUE, range_color=None, hover=None, height=520, zoom=4.8,
               legend="right"):
    """A county map of one magnitude, single-hue ramp. legend="bottom" frees the width for narrow columns."""
    import plotly.express as px

    fig = px.choropleth_map(
        df, geojson=geojson(), locations="region_fips", color=value,
        color_continuous_scale=ramp(colors), range_color=range_color,
        map_style=theme()["map_style"], opacity=0.85,
        center={"lat": 39.25, "lon": -91.65}, zoom=zoom,   # the middle of Missouri + Illinois
        hover_name="region", hover_data=hover or {value: ":.2f", "region_fips": False},
        labels={value: label},
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color=theme()["surface"])
    if legend == "bottom":
        bar = dict(title=dict(text=label, side="top"), orientation="h", thickness=10, len=0.7,
                   x=0.5, xanchor="center", y=-0.02, yanchor="top")
    else:
        bar = dict(title=label, thickness=10, len=0.6)
    fig.update_layout(coloraxis_colorbar=bar)
    return style(fig, height=height)
