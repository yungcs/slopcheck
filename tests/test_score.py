"""Score math, including the example from the README."""

from slopcheck.models import Finding
from slopcheck.score import WEIGHTS, compute_score, score_label


def _finding(severity: str) -> Finding:
    return Finding(
        rule_id="SLP001",
        rule_name="bare-except",
        severity=severity,
        message="x",
        path=__import__("pathlib").Path("a.py"),
        line=1,
        column=1,
        end_line=1,
        end_column=1,
        hint="",
        snippet="",
    )


def test_perfect_score():
    scored = compute_score([], 200)
    assert scored.value == 100
    assert scored.raw == 0
    assert scored.label == "clean"


def test_documented_example():
    findings = [_finding("error") for _ in range(5)]
    assert sum(WEIGHTS["error"] for _ in findings) == 40
    assert compute_score(findings, 200).value == 50


def test_score_decreases_with_weight():
    note = compute_score([_finding("note")], 100).value
    error = compute_score([_finding("error"), _finding("error")], 100).value
    assert 100 > note > error >= 0


def test_labels():
    assert score_label(100) == "clean"
    assert score_label(90) == "clean"
    assert score_label(75) == "light residue"
    assert score_label(50) == "needs a wash"
    assert score_label(25) == "sloppy"
    assert score_label(0) == "hazardous sludge"
