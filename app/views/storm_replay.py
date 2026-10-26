import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from lib import BLUE, ORANGE, choropleth, meta, style, table, theme

m = meta()
storms = table("storms")
preds = table("predictions")
regions = table("regions")[["region_fips", "region", "state", "customers"]]

st.title("⛈️ Storm replay")
st.markdown(
    f"The biggest outage blocks of {m['test_year']} — a year the model never trained on. "
    "Left: what the model predicted from the weather and the place. Right: what actually happened."
)

# alert level = the top 1% of predicted risk in the test year (see ml/export_app_data.py)
alert = m.get("alert_threshold", 0.5)

labels = {
    r.block_start: f"{pd.Timestamp(r.block_start):%b %d, %Y %H:00} UTC — "
                   f"{int(r.customers_out):,} out, {int(r.regions_hit)} regions ≥ {m['threshold_pct']:g}%"
    for r in storms.itertuples()
}
block = st.selectbox("Storm (6-hour block)", list(labels), format_func=labels.get)

now = preds[preds.block_start == block].merge(regions, on="region_fips")
now["pct"] = now["peak_pct_out"]
left, right = st.columns(2)
with left:
    st.subheader("Predicted risk")
    # scale to this block's highest risk: probabilities stay low even in big storms (events are rare)
    st.plotly_chart(choropleth(now, "prob", "probability", BLUE, (0, max(2 * alert, now.prob.max())), height=440,
                               hover={"prob": ":.0%", "pct": ":.1f", "region_fips": False}),
                    width="stretch")
with right:
    st.subheader("Actual peak % out")
    st.plotly_chart(choropleth(now, "pct", "% customers out", ORANGE, (0, max(10, now.pct.max())), height=440,
                               hover={"pct": ":.1f", "prob": ":.0%", "region_fips": False}),
                    width="stretch")

# the storm's timeline across the whole study area: two measures, two charts (never a dual axis)
window = preds[(preds.block_start >= pd.Timestamp(block) - pd.Timedelta(days=2)) &
               (preds.block_start <= pd.Timestamp(block) + pd.Timedelta(days=2))]
timeline = window.groupby("block_start").agg(out=("peak_out", "sum"),
                                             regions_flagged=("prob", lambda p: (p >= alert).sum()),
                                             regions_hit=("y", "sum")).reset_index()
t = theme()
a, b = st.columns(2)
with a:
    fig = go.Figure(go.Scatter(x=timeline.block_start, y=timeline.out, mode="lines+markers",
                               line=dict(color=t["series"][1], width=2), marker=dict(size=8),
                               hovertemplate="%{x|%b %d %H:00}<br>%{y:,} customers out<extra></extra>"))
    fig.add_vline(x=pd.Timestamp(block), line_dash="dot", line_color=t["muted"])
    st.plotly_chart(style(fig.update_layout(title="Customers out (all regions, peak per block)"), height=300),
                    width="stretch")
with b:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timeline.block_start, y=timeline.regions_flagged, name="flagged by model (top 1% risk)",
                             mode="lines+markers", line=dict(color=t["series"][0], width=2), marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=timeline.block_start, y=timeline.regions_hit,
                             name=f"actually ≥ {m['threshold_pct']:g}% out",
                             mode="lines+markers", line=dict(color=t["series"][1], width=2), marker=dict(size=8)))
    fig.add_vline(x=pd.Timestamp(block), line_dash="dot", line_color=t["muted"])
    fig.update_traces(hovertemplate="%{x|%b %d %H:00}<br>%{y} regions<extra>%{fullData.name}</extra>")
    st.plotly_chart(style(fig.update_layout(title="Regions"), height=300), width="stretch")

with st.expander("Table view"):
    st.dataframe(now[["region", "state", "prob", "pct", "peak_out", "gust_max_ms", "cape_max_jkg",
                      "precip_sum_mm", "storm_reports"]].sort_values("prob", ascending=False),
                 hide_index=True, width="stretch",
                 column_config={"prob": st.column_config.ProgressColumn("predicted", format="percent",
                                                                        min_value=0, max_value=1),
                                "pct": st.column_config.NumberColumn("% out", format="%.1f")})
