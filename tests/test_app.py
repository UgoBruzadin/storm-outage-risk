"""Every dashboard page must render from the synthetic test fixture without errors.

Streamlit's AppTest runs a page script headlessly and records exceptions,
so this catches broken imports, renamed columns, or a chart call that
raises — without a browser.
"""
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

PAGES = ["overview", "storm_replay", "accuracy", "scorecard", "model"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(str(ROOT / "app" / "views" / f"{page}.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


def test_storm_replay_shows_the_animation_and_timelines():
    at = AppTest.from_file(str(ROOT / "app" / "views" / "storm_replay.py"), default_timeout=60).run()
    assert len(at.get("plotly_chart")) == 2          # the two timelines; the maps are the D3 component


def test_d3_component_page_is_complete():
    """The assembled component carries D3, its data, the shared code and its own script, once each."""
    import lib
    captured = {}
    lib_components = __import__("streamlit.components.v1", fromlist=["html"])
    original = lib_components.html
    lib_components.html = lambda html, height: captured.update(html=html, height=height)
    try:
        lib.d3_component("storm", {"frames": [], "selected": 0}, height=500)
    finally:
        lib_components.html = original
    html = captured["html"]
    assert html.count("d3.min.js") == 1 and html.count("const DATA =") == 1 and html.count("function countyMap") == 1
    assert '"states"' in html and "const frames = DATA.frames" in html and captured["height"] == 500


def test_ramp_is_a_valid_plotly_colorscale():
    from lib import BLUE, ramp
    scale = ramp(BLUE)
    assert scale[0][0] == 0 and scale[-1][0] == 1
    assert [c for _, c in scale] == BLUE


def test_entry_point_reloads_lib_and_renders():
    """streamlit_app.py runs (it reloads lib when lib.py or the data changed) and the default page renders."""
    import lib
    lib.loaded_stamp = None                            # as if lib was loaded before a push
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    import sys
    assert sys.modules["lib"].loaded_stamp is not None
