"""Imports that do not resolve to a real module or stdlib attribute."""

from __future__ import annotations

import ast
from pathlib import Path

from slopcheck.models import Finding
from slopcheck.parse import ParsedFile
from slopcheck.rules.support import Rule, catches_import_error, make_finding


def _relative_base(path: Path, level: int) -> Path | None:
    base = path.parent
    for _step in range(level - 1):
        if base.parent == base:
            return None
        base = base.parent
    return base


def _module_exists(base: Path, name: str) -> bool:
    if (base / f"{name}.py").is_file() or (base / f"{name}.pyi").is_file():
        return True
    package = base / name
    if not package.is_dir():
        return False
    return (
        (package / "__init__.py").is_file()
        or (package / "__init__.pyi").is_file()
        or any(package.glob("*.py"))
    )


class HallucinatedImportRule(Rule):
    id = "SLP010"
    name = "hallucinated-import"
    severity = "error"
    summary = "Import does not resolve to the stdlib, the project, or an installed package."
    hint = (
        "Point the import at a real module. Optional imports belong in "
        "`try/except ImportError`. Allow known extras under rules.SLP010.allowed_modules."
    )

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        resolver = getattr(ctx, "resolver")
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if isinstance(node, ast.Import):
                if catches_import_error(node, parsed.parents):
                    continue
                for alias in node.names:
                    if resolver.resolves(alias.name, file=parsed.path):
                        continue
                    findings.append(
                        make_finding(
                            self,
                            ctx,
                            parsed,
                            f"import `{alias.name}` does not resolve",
                            node=alias,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if catches_import_error(node, parsed.parents):
                    continue
                if node.level:
                    self._relative(node, parsed, ctx, findings)
                    continue
                module = node.module or ""
                if not resolver.resolves(module, file=parsed.path):
                    findings.append(
                        make_finding(
                            self,
                            ctx,
                            parsed,
                            f"import `{module}` does not resolve",
                            node=node,
                        )
                    )
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if resolver.missing_stdlib_attr(module, alias.name):
                        findings.append(
                            make_finding(
                                self,
                                ctx,
                                parsed,
                                f"`{alias.name}` is not an attribute of `{module}`",
                                node=alias,
                            )
                        )
        return findings

    def _relative(
        self,
        node: ast.ImportFrom,
        parsed: ParsedFile,
        ctx: object,
        findings: list[Finding],
    ) -> None:
        base = _relative_base(parsed.path, node.level)
        if base is None:
            return
        if node.module:
            current = base
            for part in node.module.split("."):
                if not _module_exists(current, part):
                    findings.append(
                        make_finding(
                            self,
                            ctx,
                            parsed,
                            f"relative import `{'.' * node.level}{node.module}` does not resolve",
                            node=node,
                        )
                    )
                    return
                package = current / part
                current = package if package.is_dir() else current
            return
        for alias in node.names:
            if alias.name == "*" or _module_exists(base, alias.name):
                continue
            findings.append(
                make_finding(
                    self,
                    ctx,
                    parsed,
                    f"relative import `{alias.name}` does not resolve",
                    node=alias,
                )
            )
