"""Set the alert level: what acting on more or fewer alerts would have done in 2025 (ml/export_hourly.py)."""
import plotly.graph_objects as go
import streamlit as st
from lib import meta_hourly, style, table, text, theme

m, t = meta_hourly(), theme()
curves = table("alert_curves")
OFFICIAL = "Warnings + outlook"
dollars = lambda v: ("−" if v < 0 else "") + f"${abs(v) / 1e6:,.1f}M"     # noqa: E731
as_percent = lambda v: f"{v * 100:.2f}".rstrip("0").rstrip(".") + "%"      # noqa: E731  0.0075 -> "0.75%"
STYLES = {text("alert_level.style_steady"): m["headline_model"],
          text("alert_level.style_fast"): "With HRRR forecasts (newest run)"}

st.title(text("alert_level.title"))
st.markdown(text("alert_level.intro"))

left, right = st.columns([1.1, 1])
with left:
    style_label = st.radio(text("alert_level.style"), list(STYLES), help=text("alert_level.style_help"))
    model = STYLES[style_label]
    mine = curves[curves.model == model].sort_values("alert_share")
    shares = mine.alert_share.tolist()
    default = m["headline_share"] if m["headline_share"] in shares else shares[0]
    share = st.select_slider(text("alert_level.share"), options=shares, value=default,
                             format_func=lambda v: text("alert_level.share_label", share=as_percent(v)))
with right:
    cut = st.radio(text("alert_level.crew"), [10, 25], index=0, format_func=lambda v: f"{v}% shorter", horizontal=True)
    cost = st.radio(text("alert_level.cost"), [5, 20], index=0, format_func=lambda v: f"${v},000", horizontal=True)
money = f"net_cut{cut}_cost{cost}k"

row = mine[mine.alert_share == share].iloc[0]
n_new = m["n_new_outages"]
c1, c2, c3, c4 = st.columns(4)
c1.metric(text("alert_level.tile_spells"), f"{row.episodes:,.0f}", help=text("alert_level.tile_spells_help"))
caught_detail = text("alert_level.tile_caught_detail", n=f"{round(row.caught * n_new):,}", of=f"{n_new:,}")
c2.metric(text("alert_level.tile_caught"), f"{row.caught:.0%}", help=caught_detail)
c3.metric(text("alert_level.tile_real"), f"{row.precision:.0%}")
c4.metric(text("alert_level.tile_money"), dollars(row[money]), help=text("alert_level.tile_money_help"))
best = mine.loc[mine[money].idxmax()]
st.markdown(text("alert_level.best", share=as_percent(best.alert_share), money=dollars(best[money]),
                 spells=f"{best.episodes:,.0f}"))

official = curves[curves.model == OFFICIAL]
near = official.iloc[(official.actual_share - row.actual_share).abs().argmin()]
st.markdown(text("alert_level.official", caught=f"{near.caught:.0%}", real=f"{near.precision:.0%}",
                 spells=f"{near.episodes:,.0f}"))

# --- the whole trade-off -------------------------------------------------------------
colors = {model: t["series"][0], OFFICIAL: t["muted"]}
names = {model: style_label.split(" (")[0], OFFICIAL: "Official warnings + outlook"}
left, right = st.columns(2)
with left:
    fig = go.Figure()
    for name in (model, OFFICIAL):
        d = curves[curves.model == name].sort_values("episodes")
        fig.add_trace(go.Scatter(x=d.episodes, y=d.caught, mode="lines+markers", name=names[name],
                                 line=dict(color=colors[name], width=3 if name == model else 2),
                                 hovertemplate="%{x:,.0f} spells: %{y:.0%} caught<extra></extra>"))
    fig.add_trace(go.Scatter(x=[row.episodes], y=[row.caught], mode="markers", showlegend=False,
                             marker=dict(size=16, color=colors[model], line=dict(color=t["surface"], width=3)),
                             hoverinfo="skip"))
    fig.update_layout(title=text("alert_level.chart_caught"), xaxis_title=text("alert_level.axis_spells"),
                      yaxis_title=text("alert_level.axis_caught"), yaxis_tickformat=".0%")
    st.plotly_chart(style(fig, height=380), width="stretch")
with right:
    fig = go.Figure()
    for name in (model, OFFICIAL):
        d = curves[curves.model == name].sort_values("alert_share")
        fig.add_trace(go.Scatter(x=d.actual_share, y=d[money] / 1e6, mode="lines+markers", name=names[name],
                                 line=dict(color=colors[name], width=3 if name == model else 2),
                                 hovertemplate="alerts on %{x:.2%} of hours: $%{y:,.1f}M<extra></extra>"))
    fig.add_trace(go.Scatter(x=[row.actual_share], y=[row[money] / 1e6], mode="markers", showlegend=False,
                             marker=dict(size=16, color=colors[model], line=dict(color=t["surface"], width=3)),
                             hoverinfo="skip"))
    fig.add_hline(y=0, line_color=t["axis"])
    fig.update_layout(title=text("alert_level.chart_money"), xaxis_title="share of county-hours on alert",
                      yaxis_title=text("alert_level.axis_money"), xaxis_tickformat=".1%", xaxis_type="log")
    st.plotly_chart(style(fig, height=380), width="stretch")
st.caption(text("alert_level.money_note"))
