"""Bundled sample tree for ``slopcheck demo``."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

_PACKAGE_DEMO = "demo_data"


def _repo_demo() -> Path | None:
    """``demo/`` next to the src tree when running from a checkout."""
    candidate = Path(__file__).resolve().parent.parent.parent / "demo"
    return candidate if candidate.is_dir() else None


def _packaged_present() -> bool:
    root = resources.files("slopcheck").joinpath(_PACKAGE_DEMO)
    try:
        return root.is_dir() and any(root.iterdir())
    except (FileNotFoundError, NotADirectoryError, OSError, TypeError, AttributeError):
        return False


@contextmanager
def demo_tree() -> Iterator[tuple[Path, Path]]:
    """Yield ``(scan_target, project_root)`` for the bundled demo.

    Paths under ``project_root`` render as ``demo/taskflow/...``, matching
    the README and GIF.
    """
    if _packaged_present():
        with tempfile.TemporaryDirectory(prefix="slopcheck-demo-") as tmp:
            root = Path(tmp)
            dest = root / "demo"
            with resources.as_file(resources.files("slopcheck").joinpath(_PACKAGE_DEMO)) as real:
                shutil.copytree(real, dest)
            yield dest, root
        return

    fallback = _repo_demo()
    if fallback is None:
        raise FileNotFoundError("packaged demo samples are missing")
    yield fallback, fallback.parent
