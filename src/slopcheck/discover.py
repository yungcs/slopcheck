"""Find Python files under the paths a user asked to scan."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from slopcheck.config import Config
from slopcheck.globs import matches_any, relative

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".nox",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "site-packages",
    ".eggs",
    "htmlcov",
}
PY_SUFFIXES = {".py", ".pyi"}


class ScanError(ValueError):
    """The requested path cannot be scanned."""


def discover_root(start: Path) -> tuple[Path, Path | None]:
    """Return ``(project root, pyproject path)`` walking up from ``start``."""
    start = start.resolve()
    current = start if start.is_dir() else start.parent
    pyproject: Path | None = None
    git_root: Path | None = None
    probe = current
    while True:
        if pyproject is None and (probe / "pyproject.toml").is_file():
            pyproject = probe / "pyproject.toml"
        if (probe / ".git").exists():
            git_root = probe
            break
        if probe.parent == probe:
            break
        probe = probe.parent
    if pyproject is not None:
        return pyproject.parent, pyproject
    if git_root is not None:
        return git_root, None
    return current, None


def _skip_dirname(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.startswith(".") or name.endswith(".egg-info")


def _under(path: Path, explicit: Path) -> bool:
    path = path.resolve()
    explicit = explicit.resolve()
    if explicit.is_file():
        return path == explicit
    return path == explicit or explicit in path.parents


def _explicit_matches(pattern: str, explicit: Path, root: Path) -> bool:
    rel = relative(explicit, root)
    if explicit.is_file():
        return matches_any(rel, [pattern])
    if rel in {".", ""}:
        probe = "__probe__.py"
    else:
        probe = rel.rstrip("/") + "/__probe__.py"
    return matches_any(probe, [pattern]) or matches_any(rel, [pattern])


def is_excluded(path: Path, patterns: list[str], explicit_roots: list[Path], root: Path) -> bool:
    """True when config excludes ``path`` and the user did not opt into that tree."""
    rel = relative(path, root)
    for pattern in patterns:
        if not matches_any(rel, [pattern]):
            continue
        opted_in = False
        for explicit in explicit_roots:
            if _under(path, explicit) and _explicit_matches(pattern, explicit, root):
                opted_in = True
                break
        if not opted_in:
            return True
    return False


def _git_ignored(root: Path, paths: list[Path]) -> set[Path]:
    if not paths:
        return set()
    payload = b"\0".join(os.fsencode(path) for path in paths) + b"\0"
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin", "-z"],
            input=payload,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode not in (0, 1):
        return set()
    ignored: set[Path] = set()
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        ignored.add(Path(os.fsdecode(raw)).resolve())
    return ignored


def discover_files(targets: list[Path], root: Path, config: Config) -> list[Path]:
    """Return Python files to scan, stable-sorted and de-duplicated."""
    patterns = list(config.exclude)
    explicit = [target.resolve() for target in targets]
    found: list[Path] = []
    explicit_files: set[Path] = set()

    for target in explicit:
        if target.is_file():
            explicit_files.add(target)
            if target.suffix not in PY_SUFFIXES:
                raise ScanError(f"not a Python file: {target}")
            if not is_excluded(target, patterns, explicit, root):
                found.append(target)
            continue
        if not target.is_dir():
            raise FileNotFoundError(target)
        for dirpath, dirnames, filenames in os.walk(target):
            kept: list[str] = []
            for name in dirnames:
                if _skip_dirname(name):
                    continue
                child = Path(dirpath) / name
                probe = child / "__probe__.py"
                if is_excluded(probe, patterns, explicit, root):
                    continue
                kept.append(name)
            dirnames[:] = kept
            for name in filenames:
                path = Path(dirpath) / name
                if path.suffix not in PY_SUFFIXES:
                    continue
                if path.is_file() and not is_excluded(path, patterns, explicit, root):
                    found.append(path)

    ignored = _git_ignored(root, [path for path in found if path.resolve() not in explicit_files])
    unique = []
    seen: set[Path] = set()
    for path in found:
        resolved = path.resolve()
        if resolved in seen:
            continue
        if resolved not in explicit_files and resolved in ignored:
            continue
        seen.add(resolved)
        unique.append(resolved)
    unique.sort()
    return unique
