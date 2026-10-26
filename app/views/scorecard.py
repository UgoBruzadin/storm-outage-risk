import streamlit as st
from lib import table

regions = table("regions")
start, end = str(regions.history_start.iloc[0])[:4], int(str(regions.history_end.iloc[0])[:4]) - 1

st.title("📋 Resilience scorecard")
st.markdown(
    f"How each region fared in {start}–{end}, from 15-minute outage records grouped into 6-hour blocks. "
    "An **event** is a run of blocks with ≥ 1% of customers out."
)

state = st.selectbox("State", ["All states", *sorted(regions.state.unique())])
df = regions if state == "All states" else regions[regions.state == state]
st.dataframe(
    df[["region", "state", "customers", "hours_out_per_customer", "events_per_year", "storm_hit_rate",
        "quiet_event_rate", "repeat_7d_share", "canopy_mean_pct", "share_homes_pre1960", "housing_per_km2"]]
      .sort_values("hours_out_per_customer", ascending=False),
    hide_index=True, width="stretch", height=640,
    column_config={
        "customers": st.column_config.NumberColumn(
            "customers", format="localized",
            help="Electric customers in the region (EAGLE-I modeled customer counts)."),
        "hours_out_per_customer": st.column_config.NumberColumn(
            "outage h / customer / yr", format="%.1f",
            help="Customer-hours without power per customer per year (EAGLE-I outage records)."),
        "events_per_year": st.column_config.NumberColumn(
            "events / yr", format="%.1f", help="Runs of 6-hour blocks with ≥ 1% of customers out, per year."),
        "storm_hit_rate": st.column_config.ProgressColumn(
            "storm hit rate", format="percent", min_value=0, max_value=0.35,
            help="Of the 6-hour blocks with a NOAA Storm Events report in the region, the share where ≥ 1% of "
                 "customers lost power. Compares places under similar weather: closest to vulnerability."),
        "quiet_event_rate": st.column_config.NumberColumn(
            "events w/o storm", format="percent",
            help="Of the 6-hour blocks without a storm report, the share where ≥ 1% of customers lost power."),
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
    "Storm hit rate compares places under similar conditions (blocks with a NOAA storm report), so it's closer to "
    "vulnerability than raw outage counts. Repeats within 7 days are mostly storm clustering, not repair quality."
)
