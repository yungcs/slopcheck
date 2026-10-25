"""Inline ``# slopcheck:`` directives."""

from __future__ import annotations

import re

from slopcheck.parse import extract_comments

_IGNORE = re.compile(r"slopcheck:\s*ignore\b", re.IGNORECASE)
_DISABLE = re.compile(
    r"slopcheck:\s*(disable|enable)(?:\s*=\s*([A-Za-z0-9_,\s]+))?",
    re.IGNORECASE,
)
def _id_list(raw: str | None) -> set[str]:
    if not raw or not raw.strip():
        return set()
    return {part.strip().upper() for part in raw.split(",") if part.strip()}


def parse_ignore(text: str) -> set[str] | None:
    """Return ignored rule ids. Empty set means every rule. None means no tag."""
    match = _IGNORE.search(text)
    if match is None:
        return None
    rest = text[match.end() :]
    bracket = re.match(r"\s*\[([^\]]*)\]", rest)
    if bracket is not None:
        return _id_list(bracket.group(1))
    bare = re.match(r"\s+([A-Za-z]+[0-9]+(?:\s*,\s*[A-Za-z]+[0-9]+)*)", rest)
    if bare is not None:
        return _id_list(bare.group(1))
    return set()


class IgnoreMap:
    """Per-line ignores and file-level disable ranges."""

    def __init__(self) -> None:
        self.line_all: set[int] = set()
        self.line_rules: dict[int, set[str]] = {}
        self.disabled_all: dict[int, bool] = {}
        self.disabled_rules: dict[int, set[str]] = {}

    def ignores(self, line: int, rule_id: str, end_line: int | None = None) -> bool:
        """True when this rule is silenced on the finding's span."""
        last = end_line if end_line is not None else line
        for current in range(line, last + 1):
            if current in self.line_all:
                return True
            if rule_id in self.line_rules.get(current, ()):
                return True
        if self.disabled_all.get(line, False):
            return True
        return rule_id in self.disabled_rules.get(line, ())


def _add(ignore_map: IgnoreMap, line: int, rules: set[str]) -> None:
    if not rules:
        ignore_map.line_all.add(line)
        return
    ignore_map.line_rules.setdefault(line, set()).update(rule.upper() for rule in rules)


def build_ignore_map(source: str, rule_ids: set[str]) -> IgnoreMap:
    """Parse ignore and disable comments in source order."""
    lines = source.splitlines()
    comments, code_lines = extract_comments(source)
    by_line: dict[int, list[str]] = {}
    for line, _column, text in comments:
        by_line.setdefault(line, []).append(text)

    ignore_map = IgnoreMap()
    for line, texts in by_line.items():
        code_before = line in code_lines
        for text in texts:
            parsed = parse_ignore(text)
            if parsed is None:
                continue
            _add(ignore_map, line, parsed)
            if not code_before:
                nxt = line + 1
                while nxt <= len(lines) and not lines[nxt - 1].strip():
                    nxt += 1
                if nxt <= len(lines):
                    _add(ignore_map, nxt, parsed)

    disabled_all = False
    disabled: set[str] = set()
    last = len(lines)
    for line_no in range(1, last + 1):
        for text in by_line.get(line_no, []):
            match = _DISABLE.search(text)
            if match is None:
                continue
            action = match.group(1).lower()
            ids = _id_list(match.group(2))
            if action == "disable":
                if not ids:
                    disabled_all = True
                    disabled.clear()
                else:
                    disabled.update(ids)
            elif not ids:
                disabled_all = False
                disabled.clear()
            elif disabled_all:
                disabled_all = False
                disabled = set(rule_ids) - ids
            else:
                disabled.difference_update(ids)
        ignore_map.disabled_all[line_no] = disabled_all
        ignore_map.disabled_rules[line_no] = set(disabled)
    return ignore_map
