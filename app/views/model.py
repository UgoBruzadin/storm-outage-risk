import plotly.graph_objects as go
import streamlit as st
from lib import meta, style, table, theme

m = meta()
results = table("metrics")
importance = table("importance")
t = theme()
BASELINES = {"prior", "climatology", "nws_warnings", "spc_outlook", "official"}
SPLITS = {"time": "Next year (test 2025)", "county": "Unseen counties (5-fold by region)",
          "random": "Random region-days (leaky, for comparison)"}

st.title("📈 Model benchmark")
st.markdown(
    "Predicting whether a region loses power at scale in a 6-hour block from HRRR storm ingredients plus "
    "place and recent-outage features. Scores are **PR-AUC**; for rare events, no skill = the event "
    "rate, so **lift** "
    "(PR-AUC ÷ event rate) compares fairly. **New outages** = blocks whose previous 6 hours weren't already an "
    "event: outages persist, so scoring every block rewards \"it's out, it'll stay out\". "
    "Every run: `ml/benchmarks/*.yaml`."
)

benchmarks = sorted(results.benchmark.unique())
c1, c2, c3, c4 = st.columns(4)
bench = c1.segmented_control("Benchmark", benchmarks,
                             default="final_2025" if "final_2025" in benchmarks else benchmarks[0])
res = results[results.benchmark == (bench or benchmarks[0])]
sizes = sorted(res.threshold_pct.unique())
size = c2.segmented_control("Outage size (% of customers)", sizes, default=5 if 5 in sizes else sizes[0],
                            format_func=lambda v: f"≥ {v:g}%")
target = c3.segmented_control("Score on", ["New outages", "All blocks"], default="New outages")
trained = sorted(res.train_on.unique())
train_on = c4.segmented_control("Trained on", trained, default="all" if "all" in trained else trained[0])
res = res[(res.threshold_pct == (size if size is not None else sizes[0])) & (res.train_on == (train_on or trained[0]))]
p = "onset_" if target != "All blocks" else ""

st.subheader("Leaderboard: best run per model")
cols = st.columns(len([s for s in SPLITS if s in set(res.split_kind)]))
for col, kind in zip(cols, [s for s in SPLITS if s in set(res.split_kind)], strict=False):
    best = res[res.split_kind == kind].sort_values(p + "pr_auc").groupby("model").tail(1).sort_values(p + "pr_auc")
    colors = [t["muted"] if mdl in BASELINES else t["series"][0] for mdl in best.model]
    fig = go.Figure(go.Bar(
        x=best[p + "pr_auc"], y=best.model, orientation="h", marker_color=colors,
        marker_line_width=2, marker_line_color=t["surface"],
        text=[f"{v:.3f}" for v in best[p + "pr_auc"]], textposition="outside", cliponaxis=False,
        customdata=best[["features", p + "pr_auc_lift", p + "roc_auc", p + "precision_top1"]].to_numpy(),
        hovertemplate="%{y}<br>PR-AUC %{x:.3f} (%{customdata[1]:.1f}x chance)<br>features: %{customdata[0]}"
                      "<br>ROC-AUC %{customdata[2]:.3f} · precision@top1% %{customdata[3]:.1%}<extra></extra>"))
    fig.add_vline(x=best[p + "event_rate"].iloc[0], line_dash="dot", line_color=t["muted"])
    fig.update_layout(title=SPLITS[kind], xaxis_title="PR-AUC (dotted = no skill)",
                      xaxis_range=[0, best[p + "pr_auc"].max() * 1.2])   # room for the value labels
    col.plotly_chart(style(fig, height=320), width="stretch")
st.caption("Gray bars are baselines: *prior* = the event rate for everyone; *climatology* = each region's "
           "historical rate by month, no weather at all; *nws_warnings*, *spc_outlook*, *official* = the "
           "historical rate for each combination of NWS warnings in force and SPC outlook risk level at the "
           "block's start. Training years differ by benchmark: final_2025 trains on 2020–2024, quick on 2024.")

st.subheader("Does knowing the place help?")
family = m.get("model", "lightgbm")
abl = res[(res.model == family) & (res.features != "-")]
abl = abl.sort_values(p + "pr_auc").groupby(["split_kind", "features"]).tail(1)   # best params per feature set
order = abl.groupby("features")[p + "pr_auc_lift"].mean().sort_values().index.tolist()
fig = go.Figure()
for i, kind in enumerate([s for s in SPLITS if s in set(abl.split_kind)]):   # fixed categorical order
    rows = abl[abl.split_kind == kind].set_index("features").reindex(order)
    fig.add_trace(go.Bar(x=order, y=rows[p + "pr_auc_lift"], name=SPLITS[kind], marker_color=t["series"][i],
                         marker_line_width=2, marker_line_color=t["surface"],
                         hovertemplate="%{x}<br>%{y:.1f}x chance<extra>" + kind + "</extra>"))
fig.update_layout(barmode="group", yaxis_title=f"{family}: PR-AUC lift over chance", bargap=0.3)
st.plotly_chart(style(fig, height=400), width="stretch")
st.caption("Feature groups (ml/data.py): weather = storm ingredients; place = size, density, housing age, tree "
           "canopy; -canopy = the same without canopy; history = the region's outage record over the 3 years before "
           "the block's year; recent = outages in the previous 24 h; wet_soil = rain in the 72 h / 7 days before "
           "the block; warnings, outlook = NWS warnings and SPC outlook at the block's start.")

st.subheader("What the final model relies on")
scope = "new outages" if target != "All blocks" else "all blocks"
if "scored_on" in importance:
    importance = importance[importance.scored_on == scope]
top = importance.head(15).iloc[::-1]
fig = go.Figure(go.Bar(x=top.importance, y=top.feature, orientation="h", marker_color=t["series"][0],
                       error_x=dict(type="data", array=top["std"], color=t["muted"], thickness=1),
                       hovertemplate="%{y}: %{x:.4f}<extra></extra>"))
fig.update_layout(xaxis_title=f"drop in PR-AUC on {scope} when shuffled")
st.plotly_chart(style(fig, height=460), width="stretch")
st.caption(
    f"Final model ({m.get('config', 'benchmark config')}): {family}, features {m['features']}, trained on "
    f"{m['train_year']}, scored on {m['test_year']} ({m['test_blocks']:,} blocks, {m['test_events']:,} events). "
    f"Alert level ({m.get('alert_rule', 'top 1% risk')}): {m.get('alert_precision', float('nan')):.0%} of "
    f"alerts were real events."
)

with st.expander("All runs (table view)"):
    st.dataframe(res.drop(columns=["git_commit"], errors="ignore").sort_values(["split", p + "pr_auc"],
                 ascending=[True, False]), hide_index=True, width="stretch")
