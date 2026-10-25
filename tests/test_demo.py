"""The demo folder is intentionally dirty, except ok.py."""

from slopcheck.engine import scan
from slopcheck.rules import RULES
from tests.conftest import ROOT, rule_ids


def test_demo_hits_every_rule():
    report = scan([ROOT / "demo"])
    assert rule_ids(report) == {rule.id for rule in RULES}
    assert all(not str(finding.path).endswith("ok.py") for finding in report.findings)
    assert report.score < 90


def test_demo_ok_module_is_clean():
    report = scan([ROOT / "demo" / "taskflow" / "ok.py"])
    assert report.findings == []
    assert report.score == 100
