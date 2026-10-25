"""Shared data types for a slopcheck run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    """One rule match."""

    rule_id: str
    rule_name: str
    severity: str
    message: str
    path: Path
    line: int
    column: int
    end_line: int
    end_column: int
    hint: str
    snippet: str


@dataclass(frozen=True)
class ParseError:
    """A file that could not be parsed or read."""

    path: Path
    line: int
    column: int
    message: str
    line_count: int = 0


@dataclass
class Report:
    """Result of scanning one or more paths."""

    findings: list[Finding]
    parse_errors: list[ParseError]
    files_scanned: int
    lines_scanned: int
    score: int
    label: str
    raw: int
    budget: float
    version: str
    root: Path
    warnings: list[str] = field(default_factory=list)

    @property
    def finding_count(self) -> int:
        return len(self.findings)
