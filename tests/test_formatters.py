"""JSON, SARIF, HTML, SVG, and the agent prompt."""

import json
import xml.etree.ElementTree as ET

from slopcheck.formatters.badge import badge_svg
from slopcheck.formatters.html import render_html
from slopcheck.formatters.jsonfmt import render_json
from slopcheck.formatters.prompt import render_prompt
from slopcheck.formatters.sarif import render_sarif
from tests.conftest import ROOT, scan_source
from slopcheck.engine import scan


def test_formats_round_trip(tmp_path):
    source = (
        'def parse_payload(raw):\n'
        '    try:\n'
        '        return raw.strip()\n'
        '    except:\n'
        '        pass\n'
        '    print("DEBUG <script>alert(1)</script>")\n'
    )
    report = scan_source(tmp_path, source)
    payload = json.loads(render_json(report))
    assert payload["score"] < 100
    assert payload["findings"][0]["rule"] == "SLP001"
    sarif = json.loads(render_sarif(report))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["ruleId"] == "SLP001"
    assert len(sarif["runs"][0]["tool"]["driver"]["rules"]) == 15
    page = render_html(report)
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
    assert "SLP001" in page
    assert "SLP005" in page
    prompt = render_prompt(report)
    assert "SLP001" in prompt
    assert "behavior" in prompt
    svg = badge_svg(payload["score"])
    root = ET.fromstring(svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert str(payload["score"]) in svg


def test_perfect_badge_is_xml():
    svg = badge_svg(100)
    ET.fromstring(svg)
    assert ">100<" in svg


def test_demo_json_shape():
    report = scan([ROOT / "demo"])
    payload = json.loads(render_json(report))
    assert payload["finding_count"] == len(payload["findings"])
    assert set(payload["by_rule"]) <= {f"SLP{number:03d}" for number in range(1, 16)}
