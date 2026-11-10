"""Can we trust it? The 2025 test year in plain terms: against the official forecasts, storm by storm,
county by county, and whether its chances come true (ml/export_hourly.py)."""
import pandas as pd
import streamlit as st
from lib import BLUE, choropleth, gray_missing, meta_hourly, table, text

MIN_EVENTS = 3          # fewer new outages than this in a county: too few to judge
m = meta_hourly()
ours = m["ladder"][m["headline_model"]]
at = m["at_headline_share"][m["headline_model"]]

st.title(text("trust.title"))
st.markdown(text("trust.intro"))

c1, c2, c3, c4 = st.columns(4)
c1.metric(text("trust.tile_better"), text("trust.tile_better_value", ratio=f"{ours['ratio_vs_official']:.1f}"),
          help=text("trust.tile_better_help", lo=f"{ours['ratio_vs_official_lo']:.1f}",
                    hi=f"{ours['ratio_vs_official_hi']:.1f}"))
c2.metric(text("trust.tile_real"), text("trust.tile_real_value", n=round(1 / at["precision"])),
          help=f"{at['precision']:.0%} of alerts were followed by a new outage.")
c3.metric(text("trust.tile_caught"), f"{at['caught']:.0%}", help=f"Of {m['n_new_outages']:,} new outages in 2025.")
c4.metric(text("trust.tile_honest"), text("trust.tile_honest_value"), help=text("trust.tile_honest_help"))

# --- storm by storm ---------------------------------------------------------------
st.subheader(text("trust.storms_title"))
st.markdown(text("trust.storms_intro"))
days = table("storm_days").head(12).copy()
days["day"] = pd.to_datetime(days.day).dt.strftime("%a %-d %b")
days["model"] = (100 * days.caught_model / days.new_outages).round()
days["official"] = (100 * days.caught_official / days.new_outages).round()
st.dataframe(
    days[["day", "new_outages", "model", "official", "customers_out_peak"]], hide_index=True, width="stretch",
    column_config={
        "day": text("trust.col_day"),
        "new_outages": st.column_config.NumberColumn(text("trust.col_new")),
        "model": st.column_config.ProgressColumn(text("trust.col_model"), format="%d%%", min_value=0, max_value=100),
        "official": st.column_config.ProgressColumn(text("trust.col_official"), format="%d%%", min_value=0,
                                                    max_value=100),
        "customers_out_peak": st.column_config.NumberColumn(text("trust.col_peak"), format="localized"),
    })

# --- where it works, and whether its chances come true -------------------------------------
left, right = st.columns([1.3, 1])
with left:
    st.subheader(text("trust.map_title"))
    county = table("regions")[["region_fips", "region", "state"]].merge(table("county_hourly"), on="region_fips")
    county["share"] = county.caught_share.where(county.new_outages >= MIN_EVENTS)
    fig = choropleth(county.dropna(subset=["share"]), "share", "caught", BLUE, (0, 1), height=500, zoom=-0.7,
                     hover={"share": ":.0%", "region_fips": False}, legend="bottom")
    st.plotly_chart(gray_missing(fig, county, "share", "too few new outages to judge"), width="stretch")
    st.caption(text("trust.map_note", min=MIN_EVENTS))
with right:
    st.subheader(text("trust.calib_title"))
    calib = table("calibration")
    st.dataframe(pd.DataFrame({
        text("trust.col_predicted"): calib.mean_probability.map(lambda v: f"{v:.1%}"),
        text("trust.col_happened"): calib.outage_share.map(lambda v: f"{v:.1%}"),
        text("trust.col_count"): calib.decisions,
    }), hide_index=True, width="stretch",
        column_config={text("trust.col_count"): st.column_config.NumberColumn(format="localized")})
