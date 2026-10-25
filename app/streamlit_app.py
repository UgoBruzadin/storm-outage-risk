"""Storm Outage Risk — dashboard entry point.

Run locally:  pixi run app      (after pixi run export-app)
"""
import streamlit as st

st.set_page_config(page_title="Storm Outage Risk", page_icon="⚡", layout="wide")

pages = st.navigation([
    st.Page("views/overview.py", title="Overview", icon="🗺️", default=True),
    st.Page("views/storm_replay.py", title="Storm replay", icon="⛈️"),
    st.Page("views/scorecard.py", title="Resilience scorecard", icon="📋"),
    st.Page("views/model.py", title="Model", icon="📈"),
])
pages.run()
