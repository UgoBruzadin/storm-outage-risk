import streamlit as st
from lib import BLUE, choropleth, meta, table

m = meta()
regions = table("regions")
preds = table("predictions")

st.title("⚡ Storm Outage Risk — Missouri & Illinois")
st.markdown(
    "Which counties lose power when storms hit — and **why some places are hit much harder** "
    "by the same weather? A model trained on {train} predicts every 6-hour block of {test} for "
    "{n} regions, from storm ingredients (wind, shear, instability, rain, ice), what we know about "
    "each place (size, tree canopy, housing age, density) and outages in the previous 24 hours.".format(
        train=m["train_year"], test=m["test_year"], n=m["n_regions"])
)

# headline results on new outages, from the exported predictions (same rule as the Accuracy tab)
onsets = preds[preds.is_onset]
flagged = onsets.prob >= m["onset_alert_threshold"]
base_rate, hit_rate = onsets.y.mean(), onsets.y[flagged].mean()
size = f"≥ {m['threshold_pct']:g}%"
c1, c2, c3, c4 = st.columns(4)
c1.metric("Counties", f"{len(regions)}", help="Missouri and Illinois; St. Louis City and County are one region.")
c2.metric("Top alerts vs average", f"{hit_rate / base_rate:.0f}×",
          help=f"The riskiest 1% of calm county-periods in {m['test_year']} became a {size} outage "
               f"{hit_rate:.0%} of the time, against {base_rate:.1%} on average.")
c3.metric("New outages caught", f"{(flagged & (onsets.y == 1)).sum() / onsets.y.sum():.0%}",
          help=f"Share of all {int(onsets.y.sum()):,} new {size} outages in {m['test_year']} that fell in a "
               "flagged block.")
c4.metric(f"Year tested ({m['test_year']})", "never seen",
          help=f"Trained on {m['train_year']}; settings chosen on the year before the test year.")
st.link_button("The two-minute story →", "https://ugobruzadin.github.io/storm-outage-risk/")

metric = st.segmented_control(
    "Map",
    ["Outage hours per customer", "Storm hit rate", "Tree canopy", f"Mean predicted risk ({m['test_year']})"],
    default="Outage hours per customer",
)
by_region = preds.groupby("region_fips", as_index=False)["prob"].mean()
df = regions.merge(by_region, on="region_fips", how="left")
config = {
    "Outage hours per customer": ("hours_out_per_customer", "hours / year", None),
    "Storm hit rate": ("storm_hit_rate", "share of storm blocks", None),
    "Tree canopy": ("canopy_mean_pct", "% canopy", (0, 75)),
    f"Mean predicted risk ({m['test_year']})": ("prob", "mean probability", None),
}
value, label, rng = config[metric or "Outage hours per customer"]
st.plotly_chart(choropleth(df, value, label, BLUE, rng, height=600, zoom=5.6), width="stretch")
start = str(regions.history_start.iloc[0])[:4]
end = int(str(regions.history_end.iloc[0])[:4]) - 1
st.caption(
    f"Outage hours per customer and storm hit rate are the {start}–{end} scorecard (see Resilience scorecard). "
    "Storm hit rate = share of 6-hour blocks with a NOAA storm report in which ≥ 1% of customers lost power. "
    "St. Louis City and County are one region: EAGLE-I mixes their records in 2020–2024."
)
