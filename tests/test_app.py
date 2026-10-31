"""Every dashboard page must render from the synthetic test fixture without errors.

Streamlit's AppTest runs a page script headlessly and records exceptions,
so this catches broken imports, renamed columns, or a chart call that
raises — without a browser. The fixture (conftest.py) is made-up data in the
real tables' shape; it checks the pages work, never the results.
"""
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

PAGES = ["storm_room", "alert_level", "trust", "scorecard", "about"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(str(ROOT / "app" / "views" / f"{page}.py"), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]


def test_every_text_key_the_app_uses_is_in_text_yaml():
    import re

    import lib
    keys = set()
    for path in (ROOT / "app").rglob("*.py"):
        keys |= set(re.findall(r'\btext\(\s*"([\w.]+)"', path.read_text()))
    assert keys
    missing = []
    for key in sorted(keys):
        try:
            lib.text(key)
        except KeyError:
            missing.append(key)
    assert not missing, f"app/text.yaml is missing {missing}"


def test_storm_room_lists_counties_and_offers_the_csv():
    at = AppTest.from_file(str(ROOT / "app" / "views" / "storm_room.py"), default_timeout=60).run()
    assert len(at.get("dataframe")) == 1 and len(at.metric) == 3
