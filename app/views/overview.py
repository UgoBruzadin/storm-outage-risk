"""Overview: what it predicts, how well, that it runs live, and who built it. Everything a first visit needs."""
import streamlit as st
from lib import kicker, live_latest, meta_hourly, stat_row, study_area, text

m = meta_hourly()
ours = m["ladder"][m["headline_model"]]
at = m["at_headline_share"]

area = study_area()
kicker(text("overview.kicker", states=", ".join(area["states"])))
st.title(text("overview.title"))
st.markdown(text("overview.lead", counties=area["counties"], where=area["where"]))

live = live_latest()
stat_row([
    (f"{ours['ratio_vs_official']:.1f}×", text("overview.stat_ratio",
                                              lo=f"{ours['ratio_vs_official_lo']:.1f}",
                                              hi=f"{ours['ratio_vs_official_hi']:.1f}")),
    (f"{at[m['headline_model']]['caught']:.0%}", text("overview.stat_caught",
                                                     official=f"{at['Warnings + outlook']['caught']:.0%}")),
    (text("overview.stat_live_value"), text("overview.stat_live", last=live["when"]) if live
     else text("overview.stat_live_down")),
])

st.markdown(text("overview.method"))

left, right = st.columns([3, 2], gap="large")
with left:
    st.subheader(text("overview.tour_title"))
    for page, blurb in text("overview.tour").items():
        st.page_link(f"views/{page}.py", label=text(f"app.pages.{page}"), icon=":material/arrow_forward:")
        st.caption(blurb)
with right:
    with st.container(border=True):
        kicker(text("overview.me_kicker"))
        st.markdown(text("overview.me"))
