"""SARIF 2.1.0 for GitHub code scanning."""

from __future__ import annotations

import json

from slopcheck.globs import relative
from slopcheck.models import Report
from slopcheck.rules import RULES

_LEVEL = {"error": "error", "warning": "warning", "note": "note"}


def render_sarif(report: Report) -> str:
    """Serialize the report as SARIF."""
    rules = []
    index = {}
    for position, rule in enumerate(RULES):
        index[rule.id] = position
        rules.append(
            {
                "id": rule.id,
                "name": rule.name,
                "shortDescription": {"text": rule.summary},
                "fullDescription": {"text": rule.summary},
                "help": {"text": rule.hint, "markdown": rule.hint},
                "defaultConfiguration": {"level": _LEVEL.get(rule.severity, "warning")},
                "properties": {"tags": ["slop", "ai"], "precision": "high"},
            }
        )
    results = []
    for finding in report.findings:
        rel = relative(finding.path, report.root)
        region: dict[str, object] = {
            "startLine": finding.line,
            "startColumn": finding.column,
            "endLine": max(finding.end_line, finding.line),
            "endColumn": max(finding.end_column, finding.column),
        }
        if finding.snippet:
            region["snippet"] = {"text": finding.snippet}
        results.append(
            {
                "ruleId": finding.rule_id,
                "ruleIndex": index.get(finding.rule_id, 0),
                "level": _LEVEL.get(finding.severity, "warning"),
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": rel, "uriBaseId": "%SRCROOT%"},
                            "region": region,
                        }
                    }
                ],
                "partialFingerprints": {
                    "primaryLocationLineHash": (
                        f"{finding.rule_id}:{rel}:{finding.line}:{finding.column}"
                    )
                },
            }
        )
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "slopcheck",
                        "version": report.version,
                        "rules": rules,
                    }
                },
                "results": results,
                "originalUriBaseIds": {
                    "%SRCROOT%": {"uri": report.root.resolve().as_uri() + "/"}
                },
                "properties": {"slopScore": report.score, "label": report.label},
            }
        ],
    }
    return json.dumps(payload, indent=2) + "\n"
