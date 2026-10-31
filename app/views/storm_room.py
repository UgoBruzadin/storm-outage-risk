"""Storm room: a 2025 storm replayed hour by hour, as a dispatcher would have seen it two hours ahead."""
import pandas as pd
import streamlit as st
from lib import BLUE, ORANGE, choropleth, gray_missing, meta_hourly, table, text

m = meta_hourly()
regions = table("regions")
storms = table("hourly_storms").merge(regions[["region_fips", "region", "state"]], on="region_fips")
clock = lambda t: {0: "midnight", 12: "noon"}.get(t.hour, f"{t:%-I %p}")     # noqa: E731
ct = lambda ts: pd.Timestamp(ts).tz_localize("UTC").tz_convert("America/Chicago")     # noqa: E731

st.title(text("storm_room.title"))
st.markdown(text("storm_room.intro"))

# --- pick a storm and an hour ------------------------------------------------
peaks = storms.groupby("storm").agg(peak=("peak", "first"), out=("customers_out_peak", "first")).sort_values("peak")
labels = {k: f"{ct(r.peak):%a %-d %b %Y} · {r.out:,.0f} customers out at the worst hour" for k, r in peaks.iterrows()}
biggest = int(peaks.out.idxmax())
storm = st.selectbox(text("storm_room.storm"), list(labels), index=list(labels).index(biggest), format_func=labels.get)
s = storms[storms.storm == storm].sort_values(["region_fips", "hour"])

# each hour t is a window start: the forecast was made LEAD hours earlier. What happened counts new outages only:
# the worst share out in t ... t+5, for counties where a fresh new outage started in those hours
ahead = lambda v: v[::-1].rolling(6, min_periods=1).max()[::-1]      # noqa: E731  max over this hour and the next 5
s["worst_6h"] = s.groupby("region_fips").pct_out.transform(ahead)
s["new_6h"] = s.groupby("region_fips").new_outage.transform(lambda v: ahead(v.astype(float))) > 0
s["worst_6h"] = s.worst_6h.where(s.new_6h, 0.0)
hours = sorted(s.hour.unique())
risk_by_hour = s.groupby("hour").p_mean.sum()
default = risk_by_hour.idxmax() if risk_by_hour.notna().any() else hours[0]       # the hour with the most risk ahead
lead = pd.Timedelta(hours=m["lead_hours"])
hour = st.select_slider(text("storm_room.hour"), options=hours, value=default, help=text("storm_room.hour_help"),
                        format_func=lambda h: f"{ct(pd.Timestamp(h) - lead):%a %-d %b, %-I %p}")
now = s[s.hour == hour].copy()
decided, start = ct(pd.Timestamp(hour) - lead), ct(hour)
st.markdown(text("storm_room.situation", decided=f"{decided:%-I %p} on {decided:%a %-d %b}",
                 window=f"{clock(start)} and {clock(start + pd.Timedelta(hours=6))}"))

# --- the answer, in three numbers ----------------------------------------------
on_alert = now[now.p_mean > m["alert_level"]]
c1, c2, c3 = st.columns(3)
c1.metric(text("storm_room.tile_alerts"), f"{len(on_alert)}", help=text("storm_room.tile_alerts_help"))
c2.metric(text("storm_room.tile_customers"), f"{on_alert.customers.sum():,.0f}")
c3.metric(text("storm_room.tile_expected"), f"{now.p_mean.sum():.1f}", help=text("storm_room.tile_expected_help"))

# --- maps -----------------------------------------------------------------------
reveal = st.toggle(text("storm_room.reveal"), value=False)
geo = regions[["region_fips", "region", "state"]].merge(now[["region_fips", "p_mean", "p_low", "p_high", "worst_6h"]],
                                                         on="region_fips", how="left")
left, right = st.columns(2) if reveal else (st.container(), None)
zoom = 4.7 if reveal else 5.2                       # two maps side by side: zoom out so each fits its column
with left:
    st.subheader(text("storm_room.map_risk"))
    fig = choropleth(geo.dropna(subset=["p_mean"]), "p_mean", "chance", BLUE, (0, 0.4), height=520, zoom=zoom,
                     hover={"p_mean": ":.0%", "region_fips": False}, legend="bottom")
    st.plotly_chart(gray_missing(fig, geo, "p_mean", "no forecast (weather data missing)"), width="stretch")
if reveal:
    with right:
        st.subheader(text("storm_room.map_actual"))
        fig = choropleth(geo, "worst_6h", "% out", ORANGE, (0, 25), height=520, zoom=zoom,
                         hover={"worst_6h": ":.1f", "region_fips": False}, legend="bottom")
        st.plotly_chart(fig, width="stretch")

# --- the list a dispatcher would act on ---------------------------------------------
st.subheader(text("storm_room.list_title"))
st.markdown(text("storm_room.list_intro"))
top = now.dropna(subset=["p_mean"]).sort_values("p_mean", ascending=False).head(15)
listing = pd.DataFrame({
    text("storm_room.col_county"): top.region + ", " + top.state.map({"Missouri": "MO", "Illinois": "IL"}),
    text("storm_room.col_chance"): (top.p_mean * 100).round(),
    text("storm_room.col_range"): [f"{lo:.0%}–{hi:.0%}" for lo, hi in zip(top.p_low, top.p_high, strict=True)],
    text("storm_room.col_customers"): top.customers,
})
if reveal:
    listing[text("storm_room.col_happened")] = [f"{v:.0f}% out" if v else "–" for v in top.worst_6h]
st.dataframe(listing, hide_index=True, width="stretch", column_config={
    text("storm_room.col_chance"): st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=100),
    text("storm_room.col_customers"): st.column_config.NumberColumn(format="localized"),
})
st.caption(text("storm_room.list_more", n=len(top)))
st.download_button(text("storm_room.download"), listing.to_csv(index=False).encode(),
                   file_name=f"stage-crews-{decided:%Y%m%d-%H%M}.csv", mime="text/csv")
