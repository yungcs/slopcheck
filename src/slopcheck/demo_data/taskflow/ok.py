"""The one module in this folder a person might have written."""

from __future__ import annotations

import json
from pathlib import Path


def load_task(path: Path) -> dict:
    """Load one task file."""
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _normalize_title(title: str) -> str:
    return title.strip()


def label_for(title: str) -> str:
    # Titles arrive with a trailing status tag from the importer.
    cleaned = _normalize_title(title)
    return cleaned.split(" [", 1)[0]


class MissingTask(Exception):
    pass


def require_task(payload):
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    try:
        return payload["id"]
    except KeyError as exc:
        raise MissingTask(str(payload)) from exc


try:
    import definitely_not_a_real_module_zz
except ImportError:
    definitely_not_a_real_module_zz = None
