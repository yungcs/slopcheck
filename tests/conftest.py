"""Shared helpers for slopcheck tests."""

from __future__ import annotations

from pathlib import Path

from slopcheck.config import Config
from slopcheck.engine import scan

ROOT = Path(__file__).resolve().parents[1]


def rule_ids(report) -> set[str]:
    return {finding.rule_id for finding in report.findings}


def scan_source(tmp_path: Path, source: str, name: str = "sample.py") -> object:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return scan([path], config=Config(), root=tmp_path)
