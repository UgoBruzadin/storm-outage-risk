import numpy as np
import plotly.graph_objects as go
import streamlit as st
from lib import BLUE, DARK, geojson, meta, ramp, style, table, theme

MIN_EVENTS = 3          # fewer new outages than this: too few to judge a county
m, t = meta(), theme()
regions = table("regions")
preds = table("predictions")
size = f"≥ {m['threshold_pct']:g}%"

st.title("🎯 Accuracy by county")
st.markdown(
    f"How the model did in **{m['test_year']}**, a year it never saw, county by county. Scored on **new outages** "
    f"only: blocks where {size} of customers lost power after six calm hours. The model flags the riskiest 1% of "
    f"calm county-blocks (probability ≥ {m['onset_alert_threshold']:.1%})."
)

onsets = preds[preds["is_onset"]].assign(flagged=lambda d: d["prob"] >= m["onset_alert_threshold"])
onsets["caught"] = onsets["flagged"] & (onsets["y"] == 1)
by_region = (onsets.groupby("region_fips")
                   .agg(new_outages=("y", "sum"), expected=("prob", "sum"), caught=("caught", "sum"),
                        alerts=("flagged", "sum"))
                   .reset_index())
df = regions[["region_fips", "region", "state"]].merge(by_region, on="region_fips", how="left").fillna(0)
df["share_caught"] = df["caught"] / df["new_outages"].where(df["new_outages"] > 0)
df["ratio"] = df["new_outages"] / df["expected"].where(df["expected"] > 0)
judged = df["new_outages"] >= MIN_EVENTS

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"New {size} outages", f"{int(df.new_outages.sum()):,}")
c2.metric("Caught by a flag", f"{df.caught.sum() / df.new_outages.sum():.0%}")
c3.metric("Flags that were real", f"{df.caught.sum() / df.alerts.sum():.0%}")
c4.metric(f"Counties with ≥ {MIN_EVENTS} new outages", f"{int(judged.sum())} of {len(df)}")

view = st.segmented_control("Map", ["Outages caught", "Expected vs actual"], default="Outages caught")


def county_map(values, colorscale, zmin, zmax, colorbar, hover):
    """Judged counties colored; the rest in a flat gray so a single miss never paints a county."""
    gray = t["grid"]
    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=geojson(), locations=df.loc[~judged, "region_fips"], z=np.zeros((~judged).sum()),
        colorscale=[[0, gray], [1, gray]], showscale=False, marker_line_width=0.5,
        marker_line_color=t["surface"], customdata=df.loc[~judged, ["region", "new_outages"]],
        hovertemplate="%{customdata[0]}<br>%{customdata[1]:.0f} new outages: too few to judge<extra></extra>"))
    fig.add_trace(go.Choroplethmap(
        geojson=geojson(), locations=df.loc[judged, "region_fips"], z=values[judged],
        colorscale=colorscale, zmin=zmin, zmax=zmax, marker_opacity=0.9, marker_line_width=0.5,
        marker_line_color=t["surface"], colorbar=colorbar,
        customdata=df.loc[judged, ["region", "new_outages", "caught", "expected"]], hovertemplate=hover))
    fig.update_layout(map=dict(style=t["map_style"], center={"lat": 39.3, "lon": -90.9}, zoom=5.5))
    return style(fig, height=600)


if view == "Expected vs actual":
    # log2 so "twice as many" and "half as many" sit equally far from the gray midpoint
    neutral = "#383835" if t is DARK else "#f0efec"
    diverging = [[0, BLUE[5]], [0.25, BLUE[2]], [0.5, neutral], [0.75, "#f2925f"], [1, "#9c3c16"]]
    fig = county_map(np.log2(df["ratio"].clip(0.25, 4)), diverging, -2, 2,
                     dict(title="actual ÷ expected", thickness=10, len=0.6,
                          tickvals=[-2, -1, 0, 1, 2], ticktext=["¼×", "½×", "1×", "2×", "4×"]),
                     "%{customdata[0]}<br>%{customdata[1]:.0f} new outages, model expected "
                     "%{customdata[3]:.1f}<extra></extra>")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Actual new outages ÷ the number the model expected (the sum of its probabilities over the county's calm "
        "blocks). Orange: more outages than expected, the model underrated the county. Blue: fewer, it overrated "
        f"it. Gray: fewer than {MIN_EVENTS} new outages, too few to judge."
    )
else:
    fig = county_map(df["share_caught"], ramp(BLUE), 0, 1,
                     dict(title="share caught", thickness=10, len=0.6, tickformat=".0%"),
                     "%{customdata[0]}<br>%{customdata[2]:.0f} of %{customdata[1]:.0f} new outages "
                     "flagged<extra></extra>")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Share of each county's new outages that fell in a block the model flagged. Darker: more caught. "
        f"Gray: fewer than {MIN_EVENTS} new outages, too few to judge."
    )

st.subheader("Where the model was most wrong")
worst = (df[judged].assign(off=lambda d: np.log2(d["ratio"]).abs(), caught_pct=lambda d: 100 * d["share_caught"])
                   .sort_values("off", ascending=False).head(12))
st.dataframe(
    worst[["region", "state", "new_outages", "expected", "ratio", "caught_pct"]],
    hide_index=True, width="stretch",
    column_config={
        "region": "county", "new_outages": st.column_config.NumberColumn("new outages", format="%d"),
        "expected": st.column_config.NumberColumn("expected", format="%.1f",
                                                  help="Sum of the model's probabilities over the county's calm "
                                                       "blocks: how many new outages it expected."),
        "ratio": st.column_config.NumberColumn("actual ÷ expected", format="%.2f×"),
        "caught_pct": st.column_config.ProgressColumn("caught", format="%.0f%%", min_value=0, max_value=100,
                                                      help="Share of the county's new outages the model flagged."),
    },
)
