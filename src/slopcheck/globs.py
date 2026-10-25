"""Small path helpers. Patterns understand ``**`` and trailing directories."""

from __future__ import annotations

import re
from pathlib import Path


def relative(path: Path, root: Path) -> str:
    """Repo-relative posix path, or the absolute posix path if outside root."""
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
    return rel or "."


def glob_match(path: str, pattern: str) -> bool:
    """Match a posix path against a glob. ``**`` crosses directories."""
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    regex = re.escape(pattern)
    regex = regex.replace(r"\*\*", "\x00")
    regex = regex.replace(r"\*", "[^/]*")
    regex = regex.replace(r"\?", "[^/]")
    regex = regex.replace("\x00", ".*")
    return re.fullmatch(regex, path) is not None


def matches_any(path: str, patterns: list[str]) -> bool:
    """True if ``path`` matches any exclude-style pattern."""
    for pattern in patterns:
        if glob_match(path, pattern):
            return True
        if any(token in pattern for token in "*?["):
            continue
        plain = pattern.rstrip("/")
        if plain and (path == plain or path.startswith(plain + "/")):
            return True
    return False
