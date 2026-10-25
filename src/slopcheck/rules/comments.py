"""Comments that narrate the next line, and comments that are really code."""

from __future__ import annotations

import ast
import re

from slopcheck.models import Finding
from slopcheck.parse import ParsedFile, extract_comments
from slopcheck.rules.support import Rule, make_finding

_SKIP = re.compile(
    r"(noqa|slopcheck|type:\s*ignore|pragma|pylint|nosec|fmt:|isort:|pyright|mypy|ruff:)",
    re.IGNORECASE,
)
_WHY = re.compile(
    r"\b(because|intentionally|warning|must|should|don't|do not|workaround)\b",
    re.IGNORECASE,
)
_CODE = re.compile(
    r"^(?:async\s+def|def|class|import|from|return|raise|yield|assert|for|while|with|try|"
    r"except|finally|pass|break|continue|lambda|await|@|"
    r"[A-Za-z_][\w.]*\s*(?:\(|=\s|\+=|-=|\*=|/=|%=|//=|\|=|&=))"
)
_TODO = re.compile(r"^(?:todo|fixme|xxx|note|hack)\b", re.IGNORECASE)

_TEMPLATES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(?:increment|decrement|increase|decrease)\s+(\w+)\b", re.I), "aug"),
    (re.compile(r"^(?:return|returns)\b", re.I), "return"),
    (re.compile(r"^(?:import|imports)\s+(?:the\s+)?(\w+)(?:\s+module)?$", re.I), "import"),
    (
        re.compile(
            r"^(?:define|create|declare)\s+(?:a\s+|the\s+)?(?:function|method|class|variable\s+)?(\w+)\b",
            re.I,
        ),
        "define",
    ),
    (re.compile(r"^(?:loop|iterate)\s+(?:through|over|in)\s+(\w+)\b", re.I), "for"),
    (re.compile(r"^(?:check|test)\s+if\s+(\w+)\b", re.I), "if"),
    (re.compile(r"^(?:print|output)\s+(\w+)\b", re.I), "print"),
    (re.compile(r"^(?:set|assign)\s+(\w+)\s+(?:to|=)\b", re.I), "assign"),
    (re.compile(r"^(?:call|invoke)\s+(\w+)\b", re.I), "call"),
    (re.compile(r"^this\s+(?:function|method|class)\b", re.I), "this"),
    (re.compile(r"^(?:get|fetch)\s+(?:the\s+|a\s+)?(\w+)\b", re.I), "get"),
    (re.compile(r"^(?:append|add)\s+(\w+)\s+to\s+(\w+)\b", re.I), "append"),
]
_RETURN_STOP = {
    "return",
    "returns",
    "the",
    "a",
    "an",
    "value",
    "result",
    "this",
    "function",
    "method",
    "of",
    "it",
    "out",
}


def _confirms(kind: str, match: re.Match[str], code: str) -> bool:
    stripped = code.strip()
    if kind == "aug":
        name = match.group(1)
        if re.search(rf"\b{re.escape(name)}\s*(?:\+=|-=)", code):
            return True
        return re.search(rf"\b{re.escape(name)}\s*=\s*{re.escape(name)}\s*[+-]", code) is not None
    if kind == "return":
        if not stripped.startswith("return"):
            return False
        idents = [
            item
            for item in re.findall(r"\b[A-Za-z_]\w*\b", match.string)
            if item.lower() not in _RETURN_STOP
        ]
        return not idents or any(item in code for item in idents)
    if kind == "import":
        return stripped.startswith(("import", "from")) and match.group(1) in code
    if kind == "define":
        name = match.group(1)
        if re.match(rf"(?:async\s+def|def|class)\s+{re.escape(name)}\b", stripped):
            return True
        return re.match(rf"{re.escape(name)}\s*=", stripped) is not None
    if kind == "for":
        return stripped.startswith("for ") and match.group(1) in code
    if kind == "if":
        return stripped.startswith("if ") and match.group(1) in code
    if kind == "print":
        return "print" in code
    if kind == "assign":
        return re.match(rf"{re.escape(match.group(1))}\s*=", stripped) is not None
    if kind == "call":
        return f"{match.group(1)}(" in code
    if kind == "this":
        return stripped.startswith(("def ", "async def ", "class "))
    if kind == "get":
        return "=" in code and match.group(1) in code
    if kind == "append":
        return ".append(" in code
    return False


def _looks_like_code(text: str) -> bool:
    body = text.lstrip("#").strip()
    if not body or body.startswith("!") or _SKIP.search(body) or _TODO.match(body):
        return False
    if not _CODE.match(body):
        return False
    try:
        ast.parse(body)
    except SyntaxError:
        return False
    return True


class NarratingCommentRule(Rule):
    id = "SLP004"
    name = "narrating-comment"
    severity = "note"
    summary = "Comment restates the next line (`# increment i`, `# This function does X`)."
    hint = "Delete the comment. Keep a comment only when it says something the code cannot."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        comments, code_lines = extract_comments(parsed.source)
        findings: list[Finding] = []
        total = len(parsed.lines)
        for line, column, text in comments:
            if _SKIP.search(text):
                continue
            body = text.lstrip("#").strip()
            words = body.split()
            if not body or len(words) > 12 or _WHY.search(body):
                continue
            code, code_line = _narrated_code(parsed.lines, line, column, code_lines, total)
            if code is None or code_line is None or not code.strip():
                continue
            for pattern, kind in _TEMPLATES:
                match = pattern.match(body)
                if match is None or not _confirms(kind, match, code):
                    continue
                snippet = parsed.lines[line - 1].rstrip()
                end_line = line
                if code_line != line:
                    snippet = snippet + "\n" + parsed.lines[code_line - 1].rstrip()
                    end_line = code_line
                findings.append(
                    make_finding(
                        self,
                        ctx,
                        parsed,
                        "narrating comment restates the code",
                        line=line,
                        column=column + 1,
                        end_line=end_line,
                        end_column=column + max(len(text), 1),
                        snippet=snippet,
                    )
                )
                break
        return findings


def _narrated_code(
    lines: list[str],
    line: int,
    column: int,
    code_lines: set[int],
    total: int,
) -> tuple[str | None, int | None]:
    current = lines[line - 1]
    prefix = current[:column]
    if prefix.strip():
        return prefix, line
    nxt = line + 1
    while nxt <= total and not lines[nxt - 1].strip():
        nxt += 1
    if nxt <= total and nxt in code_lines:
        return lines[nxt - 1], nxt
    return None, None


class CommentedOutCodeRule(Rule):
    id = "SLP014"
    name = "commented-out-code"
    severity = "note"
    summary = "Comments that are really code, left behind just in case."
    hint = "Delete it. Version control remembers the old line."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        comments, code_lines = extract_comments(parsed.source)
        groups: list[list[tuple[int, int, str]]] = []
        current: list[tuple[int, int, str]] = []
        for line, column, text in comments:
            if line in code_lines or not _looks_like_code(text):
                if current:
                    groups.append(current)
                    current = []
                continue
            if current and line != current[-1][0] + 1:
                groups.append(current)
                current = []
            current.append((line, column, text))
        if current:
            groups.append(current)
        findings: list[Finding] = []
        for group in groups:
            start, column, _text = group[0]
            end = group[-1][0]
            count = len(group)
            noun = "line" if count == 1 else "lines"
            snippet = "\n".join(parsed.lines[item[0] - 1].rstrip() for item in group[:3])
            findings.append(
                make_finding(
                    self,
                    ctx,
                    parsed,
                    f"commented-out code ({count} {noun})",
                    line=start,
                    column=column + 1,
                    end_line=end,
                    end_column=column + 2,
                    snippet=snippet,
                )
            )
        return findings
