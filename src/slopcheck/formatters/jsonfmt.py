"""JSON report."""

from __future__ import annotations

import json
from collections import Counter

from slopcheck.globs import relative
from slopcheck.models import Finding, Report
from slopcheck.score import WEIGHTS


def _finding(finding: Finding, root) -> dict[str, object]:
    return {
        "rule": finding.rule_id,
        "name": finding.rule_name,
        "severity": finding.severity,
        "message": finding.message,
        "path": relative(finding.path, root),
        "line": finding.line,
        "column": finding.column,
        "end_line": finding.end_line,
        "end_column": finding.end_column,
        "hint": finding.hint,
        "snippet": finding.snippet,
    }


def report_dict(report: Report) -> dict[str, object]:
    """Serialize a report."""
    by_rule = Counter(item.rule_id for item in report.findings)
    by_severity = Counter(item.severity for item in report.findings)
    return {
        "tool": "slopcheck",
        "version": report.version,
        "score": report.score,
        "label": report.label,
        "files_scanned": report.files_scanned,
        "lines_scanned": report.lines_scanned,
        "finding_count": report.finding_count,
        "raw": report.raw,
        "budget": report.budget,
        "weights": WEIGHTS,
        "findings": [_finding(item, report.root) for item in report.findings],
        "parse_errors": [
            {
                "path": relative(error.path, report.root),
                "line": error.line,
                "column": error.column,
                "message": error.message,
            }
            for error in report.parse_errors
        ],
        "by_rule": dict(sorted(by_rule.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "warnings": report.warnings,
    }


def render_json(report: Report) -> str:
    """Pretty JSON with a trailing newline."""
    return json.dumps(report_dict(report), indent=2) + "\n"
