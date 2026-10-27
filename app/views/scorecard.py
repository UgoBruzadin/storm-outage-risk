import plotly.graph_objects as go
import streamlit as st
from lib import BLUE, choropleth, style, table, theme

regions = table("regions")
yearly = table("yearly").merge(regions[["region_fips", "region", "state"]], on="region_fips")
start, end = str(regions.history_start.iloc[0])[:4], int(str(regions.history_end.iloc[0])[:4]) - 1
t = theme()

st.title("📋 Resilience scorecard")
st.markdown(
    f"How each county fared in {start}–{end}, from 15-minute outage records grouped into 6-hour periods. "
    "An **outage event** is a run of periods with ≥ 1% of customers out; the **storm hit rate** is how often a "
    "reported storm turned into one, which compares places under similar weather."
)

measures = {
    "Outage hours per customer": ("hours_out_per_customer", "hours / year", "{:.1f} h"),
    "Outage events per year": ("events_per_year", "events / year", "{:.0f}"),
    "Storm hit rate": ("storm_hit_rate", "share of storms", "{:.0%}"),
}
default = "Outage hours per customer"
measure = st.segmented_control("Map", list(measures), default=default) or default
column, label, fmt = measures[measure]
st.plotly_chart(choropleth(regions, column, label, BLUE, None, height=560, zoom=5.5,
                           hover={column: ":.2f" if column == "storm_hit_rate" else ":.1f", "region_fips": False}),
                width="stretch")

# --- one county up close ------------------------------------------------------
st.subheader("One county up close")
ranked = regions.sort_values("hours_out_per_customer", ascending=False)
names = {r.region_fips: f"{r.region}, {r.state}" for r in ranked.itertuples()}
fips = st.selectbox("County", list(names), format_func=names.get, help="Sorted by outage hours per customer.")
county = regions.set_index("region_fips").loc[fips]
peers = regions[regions.state == county.state]
c1, c2, c3, c4 = st.columns(4)
for col, (name, (key, _, form)) in zip([c1, c2, c3], measures.items(), strict=True):
    median = peers[key].median()
    col.metric(name, form.format(county[key]), delta=f"{form.format(county[key] - median)} vs {county.state} median",
               delta_color="inverse")
c4.metric("Customers", f"{county.customers:,.0f}",
          help=f"Tree canopy {county.canopy_mean_pct:.0f}% · homes built before 1960 {county.share_homes_pre1960:.0%}")

years = yearly[yearly.region_fips == fips].sort_values("year")
state_median = yearly[yearly.state == county.state].groupby("year").hours_out_per_customer.median()
left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years.year, y=years.hours_out_per_customer, name=county.region, marker_color=t["series"][0],
                         marker_line_width=2, marker_line_color=t["surface"],
                         hovertemplate="%{x}: %{y:.1f} h per customer<extra></extra>"))
    fig.add_trace(go.Scatter(x=state_median.index, y=state_median.values, name=f"{county.state} median",
                             mode="lines+markers", line=dict(color=t["muted"], width=2, dash="dot"),
                             marker=dict(size=8),
                             hovertemplate="%{x}: %{y:.1f} h (state median)<extra></extra>"))
    fig.update_layout(title="Outage hours per customer, by year", yaxis_title="hours")
    st.plotly_chart(style(fig, height=340), width="stretch")
with right:
    fig = go.Figure(go.Bar(x=years.year, y=years.worst_pct_out, marker_color=t["series"][1], marker_line_width=2,
                           marker_line_color=t["surface"], text=[f"{v:.0f}%" for v in years.worst_pct_out],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: worst 6 hours, %{y:.0f}% of customers out<extra></extra>"))
    fig.update_layout(title="Worst outage each year (% of customers out)", yaxis_title="% out",
                      yaxis_range=[0, max(10, years.worst_pct_out.max() * 1.18)])
    st.plotly_chart(style(fig, height=340), width="stretch")

with st.expander("All counties"):
    state = st.selectbox("State", ["All states", *sorted(regions.state.unique())])
    df = regions if state == "All states" else regions[regions.state == state]
    st.dataframe(
        df[["region", "state", "customers", "hours_out_per_customer", "events_per_year", "storm_hit_rate",
            "quiet_event_rate", "repeat_7d_share", "canopy_mean_pct", "share_homes_pre1960", "housing_per_km2"]]
          .sort_values("hours_out_per_customer", ascending=False),
        hide_index=True, width="stretch", height=520,
        column_config={
            "region": "county",
            "customers": st.column_config.NumberColumn(
                "customers", format="localized",
                help="Electric customers in the county (EAGLE-I modeled customer counts)."),
            "hours_out_per_customer": st.column_config.NumberColumn(
                "outage h / customer / yr", format="%.1f",
                help="Customer-hours without power per customer per year (EAGLE-I outage records)."),
            "events_per_year": st.column_config.NumberColumn(
                "events / yr", format="%.1f", help="Runs of 6-hour periods with ≥ 1% of customers out, per year."),
            "storm_hit_rate": st.column_config.ProgressColumn(
                "storm hit rate", format="percent", min_value=0, max_value=0.5,
                help="Of the 6-hour periods with a NOAA Storm Events report in the county, the share where ≥ 1% of "
                     "customers lost power. Compares places under similar weather: closest to vulnerability."),
            "quiet_event_rate": st.column_config.NumberColumn(
                "events w/o storm", format="percent",
                help="Of the 6-hour periods without a storm report, the share where ≥ 1% of customers lost power."),
            "repeat_7d_share": st.column_config.NumberColumn(
                "repeat ≤ 7 days", format="percent",
                help="Share of outage events followed by another within 7 days (mostly storm clustering)."),
            "canopy_mean_pct": st.column_config.NumberColumn(
                "tree canopy %", format="%.0f", help="Average tree canopy cover (USFS / NLCD Tree Canopy Cover 2021)."),
            "share_homes_pre1960": st.column_config.NumberColumn(
                "homes pre-1960", format="percent", help="Share of homes built before 1960 (Census ACS 2020–2024)."),
            "housing_per_km2": st.column_config.NumberColumn(
                "homes / km²", format="%.0f", help="Housing units per km² of land (Census ACS, TIGER boundaries)."),
        },
    )
st.caption(
    "Storm hit rate compares places under similar conditions (periods with a NOAA storm report), so it's closer to "
    "vulnerability than raw outage counts. Repeats within 7 days are mostly storm clustering, not repair quality."
)
