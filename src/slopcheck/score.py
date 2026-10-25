"""Slop Score: 0 is sludge, 100 is clean."""

from __future__ import annotations

from dataclasses import dataclass

WEIGHTS: dict[str, int] = {"error": 8, "warning": 4, "note": 2}


@dataclass(frozen=True)
class Score:
    """Explainable score for a set of findings."""

    value: int
    raw: int
    budget: float
    label: str


def score_label(score: int) -> str:
    """Short human label for a score."""
    if score >= 90:
        return "clean"
    if score >= 75:
        return "light residue"
    if score >= 50:
        return "needs a wash"
    if score >= 25:
        return "sloppy"
    return "hazardous sludge"


def score_bar(score: int, width: int = 10) -> str:
    """Block bar, left to right, full at 100."""
    filled = round(max(0, min(100, score)) / 100 * width)
    return "█" * filled + "░" * (width - filled)


def compute_score(findings: list[object], lines: int) -> Score:
    """Score a scan.

    ``budget = lines / 5`` and ``raw`` is the sum of severity weights.
    ``score = round(100 * budget / (budget + raw))``. No findings is 100.
    A 200-line project with five error-level findings (raw 40) scores 50.
    """
    if not findings:
        return Score(100, 0, lines / 5, score_label(100))
    raw = 0
    for finding in findings:
        severity = getattr(finding, "severity", "warning")
        raw += WEIGHTS.get(severity, WEIGHTS["warning"])
    budget = max(lines, 1) / 5
    value = round(100 * budget / (budget + raw))
    value = max(0, min(100, int(value)))
    return Score(value, raw, budget, score_label(value))
