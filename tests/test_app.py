"""Every dashboard page must render from the synthetic test fixture without errors.

Streamlit's AppTest runs a page script headlessly and records exceptions,
so this catches broken imports, renamed columns, or a chart call that
raises — without a browser.
"""
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

PAGES = ["overview", "storm_replay", "scorecard", "model"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(str(ROOT / "app" / "views" / f"{page}.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


def test_storm_replay_shows_both_maps():
    at = AppTest.from_file(str(ROOT / "app" / "views" / "storm_replay.py"), default_timeout=60).run()
    assert len(at.get("plotly_chart")) == 4          # predicted map, actual map, two timelines


def test_ramp_is_a_valid_plotly_colorscale():
    from lib import BLUE, ramp
    scale = ramp(BLUE)
    assert scale[0][0] == 0 and scale[-1][0] == 1
    assert [c for _, c in scale] == BLUE
