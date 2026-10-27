import numpy as np
import streamlit as st
from lib import d3_component, meta, shapes_order, table

MIN_EVENTS = 3          # fewer new outages than this: too few to judge a county
m = meta()
regions = table("regions")
preds = table("predictions")
size = f"≥ {m['threshold_pct']:g}%"

st.title("🎯 Accuracy by county")
st.markdown(
    f"How the model did in **{m['test_year']}**, a year it never saw, county by county. Scored on **new outages** "
    f"only: blocks where {size} of customers lost power after six calm hours. The model flags the riskiest 1% of "
    f"calm county-blocks (probability ≥ {m['onset_alert_threshold']:.1%})."
)

onsets = preds[preds["is_onset"]].assign(flagged=lambda d: d["prob"] >= m["onset_alert_threshold"])
onsets["caught"] = onsets["flagged"] & (onsets["y"] == 1)
by_region = (onsets.groupby("region_fips")
                   .agg(new_outages=("y", "sum"), expected=("prob", "sum"), caught=("caught", "sum"),
                        alerts=("flagged", "sum"))
                   .reset_index())
df = regions[["region_fips", "region", "state"]].merge(by_region, on="region_fips", how="left").fillna(0)
df["share_caught"] = df["caught"] / df["new_outages"].where(df["new_outages"] > 0)
df["ratio"] = df["new_outages"] / df["expected"].where(df["expected"] > 0)
judged = df["new_outages"] >= MIN_EVENTS

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"New {size} outages", f"{int(df.new_outages.sum()):,}")
c2.metric("Caught by a flag", f"{df.caught.sum() / df.new_outages.sum():.0%}")
c3.metric("Flags that were real", f"{df.caught.sum() / df.alerts.sum():.0%}")
c4.metric(f"Counties with ≥ {MIN_EVENTS} new outages", f"{int(judged.sum())} of {len(df)}")

order = shapes_order()
cells = df.set_index("region_fips").reindex(order)
d3_component("accuracy", {"new": [int(v) for v in cells.new_outages], "caught": [int(v) for v in cells.caught],
                          "expected": [round(float(v), 2) for v in cells.expected], "min_events": MIN_EVENTS},
             height=600)
st.caption(
    "Outages caught: the share of each county's new outages that fell in a block the model flagged; darker = more. "
    "Expected vs actual: actual new outages ÷ the number the model expected (the sum of its probabilities); orange "
    f"counties had more than expected, blue fewer. Hatched: fewer than {MIN_EVENTS} new outages, too few to judge."
)

st.subheader("Where the model was most wrong")
worst = (df[judged].assign(off=lambda d: np.log2(d["ratio"]).abs(), caught_pct=lambda d: 100 * d["share_caught"])
                   .sort_values("off", ascending=False).head(12))
st.dataframe(
    worst[["region", "state", "new_outages", "expected", "ratio", "caught_pct"]],
    hide_index=True, width="stretch",
    column_config={
        "region": "county", "new_outages": st.column_config.NumberColumn("new outages", format="%d"),
        "expected": st.column_config.NumberColumn("expected", format="%.1f",
                                                  help="Sum of the model's probabilities over the county's calm "
                                                       "blocks: how many new outages it expected."),
        "ratio": st.column_config.NumberColumn("actual ÷ expected", format="%.2f×"),
        "caught_pct": st.column_config.ProgressColumn("caught", format="%.0f%%", min_value=0, max_value=100,
                                                      help="Share of the county's new outages the model flagged."),
    },
)
