"""What it's worth: how many alerts a utility should act on, and what that would have saved in 2025
(ml/export_hourly.py). One question, one money number: the slider opens on the level that saves the most."""
import plotly.graph_objects as go
import streamlit as st
from lib import meta_hourly, stat_row, style, table, text, theme

m, t = meta_hourly(), theme()
curves = table("alert_curves")
MODEL, OFFICIAL = m["headline_model"], "Warnings + outlook"
dollars = lambda v: ("−" if v < 0 else "+") + f"${abs(v) / 1e6:,.1f}M"      # noqa: E731
as_percent = lambda v: f"{v * 100:.2f}".rstrip("0").rstrip(".") + "%"      # noqa: E731  0.0075 -> "0.75%"

st.title(text("alert_level.title"))
st.markdown(text("alert_level.intro"))

a, b = st.columns(2)
cut = a.radio(text("alert_level.crew"), [10, 25], format_func=lambda v: f"{v}% shorter", horizontal=True)
cost = b.radio(text("alert_level.cost"), [5, 20], format_func=lambda v: f"${v},000", horizontal=True)
money = f"net_cut{cut}_cost{cost}k"

mine = curves[curves.model == MODEL].sort_values("alert_share")
best = mine.loc[mine[money].idxmax()]
share = st.select_slider(                       # keyed on the assumptions, so changing them reopens on their best
    text("alert_level.share"), options=mine.alert_share.tolist(), value=best.alert_share, key=f"share_{money}",
    format_func=lambda v: text("alert_level.share_label", share=as_percent(v)))
row = mine[mine.alert_share == share].iloc[0]

n_new = m["n_new_outages"]
stat_row([
    (dollars(row[money]), text("alert_level.stat_money", cut=cut, cost=f"${cost},000")),
    (f"{row.caught:.0%}", text("alert_level.stat_caught", n=f"{round(row.caught * n_new):,}", of=f"{n_new:,}")),
    (f"{row.precision:.0%}", text("alert_level.stat_real", spells=f"{row.episodes:,.0f}")),
])
if row.alert_share == best.alert_share:
    st.markdown(text("alert_level.is_best"))
else:
    st.markdown(text("alert_level.not_best", share=as_percent(best.alert_share), money=dollars(best[money])))

official = curves[curves.model == OFFICIAL]
near = official.iloc[(official.actual_share - row.actual_share).abs().argmin()]
st.markdown(text("alert_level.official", caught=f"{near.caught:.0%}", real=f"{near.precision:.0%}",
                 money=dollars(near[money])))

# --- the whole trade-off: the chosen level as a ring, the best as a labelled point -----------------------
colors = {MODEL: t["series"][0], OFFICIAL: t["muted"]}
names = {MODEL: text("alert_level.name_model"), OFFICIAL: text("alert_level.name_official")}


TICKS = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]


def axes(fig, title, y_title, **y):
    """Log x with a few readable ticks."""
    fig.update_layout(title=title, yaxis_title=y_title, **y)
    fig.update_xaxes(type="log", title=text("alert_level.axis_share"), tickvals=TICKS,
                     ticktext=[as_percent(v) for v in TICKS])


def point(fig, x, y, label=None):
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text" if label else "markers", showlegend=False,
                             text=[label] if label else None, textposition="top center",
                             textfont=dict(color=t["ink"], size=13),
                             marker=dict(size=16 if not label else 11, color=colors[MODEL],
                                         line=dict(color=t["surface"], width=3)), hoverinfo="skip"))


left, right = st.columns(2, gap="large")
with left:
    fig = go.Figure()
    for name in (MODEL, OFFICIAL):
        d = curves[curves.model == name].sort_values("actual_share")
        fig.add_trace(go.Scatter(x=d.actual_share, y=d[money] / 1e6, mode="lines+markers", name=names[name],
                                 line=dict(color=colors[name], width=3 if name == MODEL else 2),
                                 hovertemplate="alerts on %{x:.2%} of hours: $%{y:,.1f}M<extra></extra>"))
    fig.add_hline(y=0, line_color=t["axis"])
    point(fig, best.actual_share, best[money] / 1e6, text("alert_level.best_label"))
    point(fig, row.actual_share, row[money] / 1e6)
    axes(fig, text("alert_level.chart_money"), text("alert_level.axis_money"))
    st.plotly_chart(style(fig, height=400).update_layout(legend_y=-0.3), width="stretch")
with right:
    fig = go.Figure()
    for name in (MODEL, OFFICIAL):
        d = curves[curves.model == name].sort_values("actual_share")
        fig.add_trace(go.Scatter(x=d.actual_share, y=d.caught, mode="lines+markers", name=names[name],
                                 line=dict(color=colors[name], width=3 if name == MODEL else 2),
                                 hovertemplate="alerts on %{x:.2%} of hours: %{y:.0%} caught<extra></extra>"))
    point(fig, row.actual_share, row.caught)
    axes(fig, text("alert_level.chart_caught"), text("alert_level.axis_caught"), yaxis_tickformat=".0%")
    st.plotly_chart(style(fig, height=400).update_layout(legend_y=-0.3), width="stretch")
st.caption(text("alert_level.money_note"))
