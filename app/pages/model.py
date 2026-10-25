import plotly.graph_objects as go
import streamlit as st

from lib import meta, style, table, theme

m = meta()
metrics = table("metrics")
importance = table("importance")
t = theme()

st.title("📈 Model")
st.markdown(
    f"Gradient-boosted trees predicting whether **≥ {m['threshold_pct']:g}% of a region's customers** lose power "
    "in a 6-hour block — the setup of *weathernext-outage-forecasting*, with free HRRR weather instead of "
    "WeatherNext, plus place features. Scores are **PR-AUC**: for rare events, a coin flip scores the event rate."
)

st.subheader("Does knowing the place help?")
split_names = {"time": "Next year (train 2024 → test 2025)", "county": "Unseen counties (5-fold by region)",
               "random": "Random region-days (weathernext-style, leaky)"}
sets = ["weather", "weather+place", "weather+place-canopy", "weather+place+history"]
hgb = metrics[(metrics.model == "hgb") & (metrics.threshold_pct == m["threshold_pct"])]
fig = go.Figure()
for i, name in enumerate(sets):                       # fixed categorical order, never cycled
    rows = hgb[hgb.features == name].set_index("split").reindex(list(split_names))
    fig.add_trace(go.Bar(x=[split_names[s] for s in rows.index], y=rows.pr_auc, name=name,
                         marker_color=t["series"][i], marker_line_width=2, marker_line_color=t["surface"],
                         hovertemplate="%{x}<br>" + name + ": PR-AUC %{y:.3f}<extra></extra>"))
rate = hgb.event_rate.mean()
fig.add_hline(y=rate, line_dash="dot", line_color=t["muted"], annotation_text="event rate (no skill)",
              annotation_font_color=t["muted"])
fig.update_layout(barmode="group", yaxis_title="PR-AUC", bargap=0.3)
st.plotly_chart(style(fig, height=420), width="stretch")
with st.expander("Table view"):
    st.dataframe(metrics.sort_values(["threshold_pct", "split", "model", "features"]), hide_index=True,
                 width="stretch")

st.subheader("What the final model relies on")
top = importance.head(15).iloc[::-1]
fig = go.Figure(go.Bar(x=top.importance, y=top.feature, orientation="h", marker_color=t["series"][0],
                       error_x=dict(type="data", array=top["std"], color=t["muted"], thickness=1),
                       hovertemplate="%{y}: %{x:.4f}<extra></extra>"))
fig.update_layout(xaxis_title="drop in PR-AUC when shuffled")
st.plotly_chart(style(fig, height=460), width="stretch")
st.caption(
    f"Final model: {m['features']}, trained on {m['train_year']}, scored on {m['test_year']} "
    f"({m['test_blocks']:,} blocks, {m['test_events']:,} events). Permutation importance on a sample of the test year."
)
