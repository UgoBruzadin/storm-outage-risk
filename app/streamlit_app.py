"""Storm Outage Risk — dashboard entry point.

Run locally:  pixi run app      (after pixi run export-app)
"""
import importlib
from pathlib import Path

import lib
import streamlit as st

st.set_page_config(page_title="Storm Outage Risk", page_icon="⚡", layout="wide")


def _files_stamp():
    """Latest change to lib.py or to the local exported data (an hf:// dataset can't be listed)."""
    paths = [Path(lib.__file__)]
    if not lib.APP_DATA.startswith("hf://"):
        paths += list(Path(lib.APP_DATA).glob("*"))
    return max(p.stat().st_mtime for p in paths)


# On a push, Streamlit Cloud reruns the page scripts with the new code but keeps already-imported
# modules and cached data, so pages calling new lib functions fail until a reboot. Reload lib and
# clear the data cache whenever lib.py or the data changed since lib was loaded.
stamp = _files_stamp()
if getattr(lib, "loaded_stamp", None) != stamp:
    st.cache_data.clear()
    lib = importlib.reload(lib)
    lib.loaded_stamp = stamp

pages = st.navigation([
    st.Page("views/overview.py", title="Overview", icon="🗺️", default=True),
    st.Page("views/storm_replay.py", title="Storm replay", icon="⛈️"),
    st.Page("views/accuracy.py", title="Accuracy", icon="🎯"),
    st.Page("views/scorecard.py", title="Resilience scorecard", icon="📋"),
    st.Page("views/model.py", title="Model", icon="📈"),
])
pages.run()
