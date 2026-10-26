import streamlit as st
from lib import BLUE, choropleth, meta, table

m = meta()
regions = table("regions")
preds = table("predictions")

st.title("⚡ Storm Outage Risk — Missouri & Illinois")
st.markdown(
    "Which counties lose power when storms hit — and **why some places are hit much harder** "
    "by the same weather? A model trained on {train} predicts every 6-hour block of {test} for "
    "{n} regions, from storm ingredients (wind, shear, instability, rain, ice) plus what we know "
    "about each place (tree canopy, housing age, density, past resilience).".format(
        train=m["train_year"], test=m["test_year"], n=m["n_regions"])
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Regions", f"{len(regions)}")
c2.metric(f"6-hour blocks scored ({m['test_year']})", f"{m['test_blocks']:,}")
c3.metric(f"Outage events (≥ {m['threshold_pct']:g}% out)", f"{m['test_events']:,}")
c4.metric("Event rate", f"{m['test_events'] / m['test_blocks']:.2%}")

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
st.plotly_chart(choropleth(df, value, label, BLUE, rng, height=600, zoom=5.4), width="stretch")
start = str(regions.history_start.iloc[0])[:4]
end = int(str(regions.history_end.iloc[0])[:4]) - 1
st.caption(
    f"Outage hours per customer and storm hit rate come from {start}–{end} (before the model's years). "
    "Storm hit rate = share of 6-hour blocks with a NOAA storm report in which ≥ 1% of customers lost power. "
    "St. Louis City and County are one region: EAGLE-I mixes their records in 2020–2024."
)
