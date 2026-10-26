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
        "customers": st.column_config.NumberColumn("customers", format="%,d"),
        "hours_out_per_customer": st.column_config.NumberColumn("outage h / customer / yr", format="%.1f"),
        "events_per_year": st.column_config.NumberColumn("events / yr", format="%.1f"),
        "storm_hit_rate": st.column_config.ProgressColumn("storm hit rate", format="%.0f%%",
                                                          min_value=0, max_value=0.35),
        "quiet_event_rate": st.column_config.NumberColumn("events w/o storm", format="%.1f%%"),
        "repeat_7d_share": st.column_config.NumberColumn("repeat ≤ 7 days", format="%.0f%%"),
        "canopy_mean_pct": st.column_config.NumberColumn("tree canopy %", format="%.0f"),
        "share_homes_pre1960": st.column_config.NumberColumn("homes pre-1960", format="%.0f%%"),
        "housing_per_km2": st.column_config.NumberColumn("homes / km²", format="%.0f"),
    },
)
st.caption(
    "Storm hit rate compares places under similar conditions (blocks with a NOAA storm report), so it's closer to "
    "vulnerability than raw outage counts. Repeats within 7 days are mostly storm clustering, not repair quality."
)
