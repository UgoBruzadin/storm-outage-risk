"""The story page's text lives in site/text.yaml; every key the page asks for must exist there."""
import re
from pathlib import Path

import yaml

SITE = Path(__file__).resolve().parent.parent / "site"


def lookup(text, key):
    node = text
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def test_every_text_key_on_the_story_page_is_in_text_yaml():
    html = (SITE / "index.html").read_text()
    text = yaml.safe_load((SITE / "text.yaml").read_text())
    keys = set(re.findall(r'data-t="([\w.]+)"', html))
    keys |= set(re.findall(r'\bTp?\(\s*"([\w.]+)"', html))                       # T("a.b") and Tp("a.b")
    keys |= {k for pair in re.findall(r'\bTp?\(\s*\w+ \? "([\w.]+)" : "([\w.]+)"', html) for k in pair}
    keys |= {f"{section}.menu" for section in re.findall(r'<section class="slide[^"]*" id="(\w+)"', html)}
    assert keys, "found no text keys: has the page's lookup changed?"
    missing = sorted(k for k in keys if lookup(text, k) is None)
    assert not missing, f"text.yaml is missing {missing}"


def test_text_yaml_lists_have_their_fields():
    text = yaml.safe_load((SITE / "text.yaml").read_text())
    assert all({"what", "from"} <= set(s) for s in text["data"]["sources"])
    assert all({"title", "text"} <= set(n) for n in text["end"]["next"])


def test_writeup_contents_links_point_to_headings():
    md = (SITE / "writeup" / "writeup.md").read_text()
    anchors = set(re.findall(r"^#{1,3} .+\{#([\w-]+)\}\s*$", md, flags=re.M))
    links = set(re.findall(r"\]\(#([\w-]+)\)", md))
    assert links, "found no contents links"
    assert links <= anchors, f"links with no heading: {sorted(links - anchors)}"
    body = re.sub(r"<!--.*?-->", "", md, flags=re.S)                      # the guide at the top mentions :::
    opens = len(re.findall(r"^:::[ \t]*[\w-]+[ \t]*$", body, flags=re.M))
    closes = len(re.findall(r"^:::[ \t]*$", body, flags=re.M))
    assert opens == closes, f"{opens} ::: boxes opened, {closes} closed"
