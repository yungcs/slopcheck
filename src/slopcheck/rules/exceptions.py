"""Exception-shaped slop: swallowed errors, dummy data, and deep nesting."""

from __future__ import annotations

import ast

from slopcheck.models import Finding
from slopcheck.parse import ParsedFile
from slopcheck.rules.support import (
    TRY_TYPES,
    Rule,
    enclosing_function,
    handler_reraises,
    is_broad_handler,
    is_none_or_false,
    is_swallow_body,
    make_finding,
    unparse,
    walk_skip_nested,
)

_ERROR_KEYS = {"error", "err", "errors", "success", "ok", "status", "message"}
_ERROR_PREFIXES = (
    "error",
    "err:",
    "failed",
    "failure",
    "unable",
    "something went wrong",
    "exception",
    "invalid",
    "could not",
    "couldn't",
)
_DUMMY_STRINGS = {"", "ok", "success", "none", "null", "undefined", "todo"}


def _in_exit(parents: dict[int, ast.AST], node: ast.AST) -> bool:
    function = enclosing_function(parents, node)
    return function is not None and function.name in {"__exit__", "__aexit__"}


def _exit_propagation(parents: dict[int, ast.AST], handler: ast.ExceptHandler) -> bool:
    """``return False`` from ``__exit__`` propagates; it does not fake success."""
    if not _in_exit(parents, handler):
        return False
    if len(handler.body) != 1 or not isinstance(handler.body[0], ast.Return):
        return False
    return is_none_or_false(handler.body[0].value)


def _error_text(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped.startswith(_ERROR_PREFIXES)


def _string_of(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("")
        return "".join(parts)
    return None


def is_error_payload(node: ast.AST) -> bool:
    text = _string_of(node)
    if text is not None:
        return _error_text(text)
    if isinstance(node, ast.Dict):
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                if key.value.lower() in _ERROR_KEYS:
                    return True
    return False


def is_dummy_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, str):
            return value.strip().lower() in _DUMMY_STRINGS
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return value in (0, 0.0)
        return False
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and not node.elts:
        return True
    if isinstance(node, ast.Dict) and not node.keys:
        return True
    return False


def _returns_in(handler: ast.ExceptHandler) -> list[ast.Return]:
    found: list[ast.Return] = []
    for node in walk_skip_nested(handler):
        if isinstance(node, ast.Return) and node.value is not None:
            found.append(node)
    return found


class BareExceptRule(Rule):
    id = "SLP001"
    name = "bare-except"
    severity = "error"
    summary = "Bare `except:` swallows every error, including KeyboardInterrupt and SystemExit."
    hint = (
        "Catch the specific exception you can handle, or let it propagate. "
        "A bare except also catches KeyboardInterrupt and SystemExit."
    )

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if not isinstance(node, TRY_TYPES):
                continue
            for handler in node.handlers:
                if handler.type is not None or handler_reraises(handler):
                    continue
                findings.append(
                    make_finding(
                        self,
                        ctx,
                        parsed,
                        "bare except swallows errors, including KeyboardInterrupt and SystemExit",
                        node=handler,
                    )
                )
        return findings


class BroadExceptRule(Rule):
    id = "SLP002"
    name = "broad-except-swallow"
    severity = "error"
    summary = "`except Exception` whose body only passes, continues, or returns None/False."
    hint = "Handle the specific error, or re-raise. Returning None here hides a real failure."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if not isinstance(node, TRY_TYPES):
                continue
            for handler in node.handlers:
                if not is_broad_handler(handler) or handler_reraises(handler):
                    continue
                if not is_swallow_body(handler.body):
                    continue
                if _exit_propagation(parsed.parents, handler):
                    continue
                findings.append(
                    make_finding(
                        self,
                        ctx,
                        parsed,
                        "broad except swallows the error",
                        node=handler,
                    )
                )
        return findings


class FakeFallbackRule(Rule):
    id = "SLP003"
    name = "fake-fallback"
    severity = "error"
    summary = "`except` returns an empty or dummy value and pretends the call worked."
    hint = "Return a real result or raise. An empty dict, list, or string from except is made-up data."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if not isinstance(node, TRY_TYPES):
                continue
            for handler in node.handlers:
                for ret in _returns_in(handler):
                    value = ret.value
                    if value is None or is_error_payload(value) or not is_dummy_literal(value):
                        continue
                    rendered = unparse(value) or "a dummy value"
                    findings.append(
                        make_finding(
                            self,
                            ctx,
                            parsed,
                            f"except handler returns dummy value {rendered}",
                            node=ret,
                        )
                    )
        return findings


class TryNestingRule(Rule):
    id = "SLP011"
    name = "try-nesting"
    severity = "warning"
    summary = "`try` nested deeper than the configured limit (default 2)."
    hint = "Flatten the handlers or split the function. Deeply nested try blocks hide which error is which."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        option_int = getattr(ctx, "option_int")
        limit = option_int("SLP011", "max_depth", 2)
        findings: list[Finding] = []

        def walk(node: ast.AST, depth: int) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if isinstance(child, TRY_TYPES):
                    found_depth = depth + 1
                    if found_depth > limit:
                        findings.append(
                            make_finding(
                                self,
                                ctx,
                                parsed,
                                f"try/except nested to depth {found_depth} (limit {limit})",
                                node=child,
                            )
                        )
                    walk(child, found_depth)
                else:
                    walk(child, depth)

        for node in ast.walk(parsed.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                walk(node, 0)
        return findings


class ErrorStringRule(Rule):
    id = "SLP015"
    name = "error-string-return"
    severity = "warning"
    summary = '`except` returns `"Error: ..."` or `{"success": False}` instead of raising.'
    hint = "Raise, or return a value the caller expects on purpose. An error string drops the traceback."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if not isinstance(node, TRY_TYPES):
                continue
            for handler in node.handlers:
                for ret in _returns_in(handler):
                    value = ret.value
                    if value is not None and is_error_payload(value):
                        findings.append(
                            make_finding(
                                self,
                                ctx,
                                parsed,
                                "except handler returns an error payload instead of raising",
                                node=ret,
                            )
                        )
        return findings
