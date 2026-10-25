"""Read a Python file into an AST plus comments."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path

_SKIP_TOKENS = {
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.COMMENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
    tokenize.INDENT,
    tokenize.DEDENT,
}


@dataclass
class ParsedFile:
    """One successfully parsed source file."""

    path: Path
    source: str
    lines: list[str]
    tree: ast.AST
    parents: dict[int, ast.AST]
    line_count: int


def read_source(path: Path) -> str:
    """Read source using the file's encoding cookie."""
    with tokenize.open(path) as handle:
        return handle.read()


def extract_comments(source: str) -> tuple[list[tuple[int, int, str]], set[int]]:
    """Return ``(line, column, text)`` comments and the set of lines that contain code."""
    comments: list[tuple[int, int, str]] = []
    code_lines: set[int] = set()
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                comments.append((tok.start[0], tok.start[1], tok.string))
            elif tok.type not in _SKIP_TOKENS:
                code_lines.add(tok.start[0])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return comments, code_lines
    return comments, code_lines


def parse_source(path: Path, source: str) -> ParsedFile:
    """Parse source that has already been read."""
    tree = ast.parse(source, filename=str(path))
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    lines = source.splitlines()
    return ParsedFile(
        path=path,
        source=source,
        lines=lines,
        tree=tree,
        parents=parents,
        line_count=len(lines),
    )


def line_snippet(lines: list[str], start: int, end: int, limit: int = 3) -> str:
    """Return a short source excerpt covering ``start`` through ``end``."""
    if not lines:
        return ""
    start = min(max(start, 1), len(lines))
    end = min(max(end, start), len(lines))
    if end - start + 1 > limit:
        end = start + limit - 1
    return "\n".join(lines[index].rstrip() for index in range(start - 1, end))
