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


def test_packaged_demo_matches_repo_demo():
    """Wheel samples stay in lockstep with the repo demo/ tree."""
    repo = ROOT / "demo"
    packaged = ROOT / "src" / "slopcheck" / "demo_data"
    repo_files = sorted(path.relative_to(repo).as_posix() for path in repo.rglob("*") if path.is_file())
    pkg_files = sorted(path.relative_to(packaged).as_posix() for path in packaged.rglob("*") if path.is_file())
    assert repo_files == pkg_files
    for rel in repo_files:
        assert (repo / rel).read_bytes() == (packaged / rel).read_bytes()

