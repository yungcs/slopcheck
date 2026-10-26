"""Decide whether an import points at a real module."""

from __future__ import annotations

import importlib
import importlib.metadata as importlib_metadata
import importlib.util
import sys
from pathlib import Path

# Importing these prints, opens a GUI, or depends on a display.
_SKIP_ATTR_IMPORTS = {"this", "antigravity", "turtle", "tkinter"}


class ImportResolver:
    """Resolve imports against the stdlib, the project tree, and installed distributions."""

    def __init__(self, project_root: Path, allowed: set[str] | None = None) -> None:
        self.root = project_root.resolve()
        self.allowed = {name.split(".")[0] for name in (allowed or set())}
        self.stdlib = set(sys.stdlib_module_names) | {"__future__"}
        self._installed: set[str] | None = None
        self._spec_cache: dict[str, bool] = {}
        self._module_cache: dict[str, object | None] = {}

    def _installed_top_levels(self) -> set[str]:
        if self._installed is None:
            names: set[str] = set()
            try:
                names.update(importlib_metadata.packages_distributions().keys())
            except (importlib_metadata.PackageNotFoundError, OSError, ValueError):
                names = set()
            self._installed = names
        return self._installed

    def _spec_ok(self, module: str) -> bool:
        if module in self._spec_cache:
            return self._spec_cache[module]
        exists = False
        try:
            exists = importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError, ValueError, AttributeError):
            exists = False
        self._spec_cache[module] = exists
        return exists

    def _nested_exists(self, base: Path, parts: list[str]) -> bool:
        current = base
        for index, part in enumerate(parts):
            package = current / part
            module_file = current / f"{part}.py"
            stub = current / f"{part}.pyi"
            last = index == len(parts) - 1
            if last:
                if module_file.is_file() or stub.is_file():
                    return True
                if package.is_dir() and (
                    (package / "__init__.py").is_file()
                    or (package / "__init__.pyi").is_file()
                    or any(package.glob("*.py"))
                ):
                    return True
                return False
            if (package / "__init__.py").is_file() or package.is_dir():
                current = package
                continue
            return False
        return False

    def _local_exists(self, module: str, extra_roots: list[Path]) -> bool:
        parts = module.split(".")
        if not parts or not parts[0]:
            return False
        roots = [self.root, self.root / "src", *extra_roots]
        seen: set[Path] = set()
        for root in roots:
            resolved = root.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if self._nested_exists(resolved, parts):
                return True
        return False

    def resolves(self, module: str, *, file: Path | None = None) -> bool:
        """True when ``module`` is stdlib, project-local, installed, or allowed."""
        if not module:
            return True
        top = module.split(".")[0]
        if top in self.allowed:
            return True
        if top in self.stdlib:
            return self._spec_ok(module)
        extra: list[Path] = []
        if file is not None:
            extra.append(file.parent)
        if self._local_exists(module, extra):
            return True
        if top in self._installed_top_levels():
            return self._spec_ok(module)
        # Python 3.10 builds packages_distributions() from top_level.txt only, and
        # many current wheels (rich, typer) do not ship one. Ask the import system.
        if self._spec_ok(top):
            return self._spec_ok(module)
        return False

    def missing_stdlib_attr(self, module: str, name: str) -> bool:
        """True when ``from stdlib_module import name`` names a missing attribute."""
        top = module.split(".")[0]
        if top not in self.stdlib or top in _SKIP_ATTR_IMPORTS or name == "*":
            return False
        if module not in self._module_cache:
            loaded: object | None
            try:
                loaded = importlib.import_module(module)
            except (
                ImportError,
                ModuleNotFoundError,
                AttributeError,
                OSError,
                RuntimeError,
                ValueError,
                SystemError,
                TypeError,
                SyntaxError,
            ):
                loaded = None
            self._module_cache[module] = loaded
        loaded = self._module_cache[module]
        if loaded is None:
            return False
        if hasattr(loaded, name):
            return False
        return not self._spec_ok(f"{module}.{name}")
