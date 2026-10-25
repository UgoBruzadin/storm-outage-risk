"""Storm Outage Risk — dashboard entry point.

Run locally:  pixi run app      (after pixi run export-app)
"""
import streamlit as st

st.set_page_config(page_title="Storm Outage Risk", page_icon="⚡", layout="wide")

pages = st.navigation([
    st.Page("pages/overview.py", title="Overview", icon="🗺️", default=True),
    st.Page("pages/storm_replay.py", title="Storm replay", icon="⛈️"),
    st.Page("pages/scorecard.py", title="Resilience scorecard", icon="📋"),
    st.Page("pages/model.py", title="Model", icon="📈"),
])
pages.run()
