"""Helpers shared by rules. Not a rule itself."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from slopcheck.models import Finding
from slopcheck.parse import ParsedFile, line_snippet

TRY_TYPES: tuple[type, ...] = (ast.Try,)
if hasattr(ast, "TryStar"):
    TRY_TYPES = (ast.Try, ast.TryStar)


class Rule:
    """One slopcheck rule."""

    id: str
    name: str
    severity: str
    summary: str
    hint: str

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        return []

    def check_project(self, files: list[ParsedFile], ctx: object) -> list[Finding]:
        return []


def make_finding(
    rule: Rule,
    ctx: object,
    parsed: ParsedFile,
    message: str,
    *,
    node: ast.AST | None = None,
    line: int | None = None,
    column: int | None = None,
    end_line: int | None = None,
    end_column: int | None = None,
    snippet: str | None = None,
) -> Finding:
    """Build a finding anchored on ``node`` or an explicit span."""
    if node is not None and line is None:
        line = getattr(node, "lineno", 1) or 1
        column = getattr(node, "col_offset", 0) + 1
        end_line = getattr(node, "end_lineno", None) or line
        end_column = (getattr(node, "end_col_offset", 0) or 0) + 1
    line = line or 1
    column = column or 1
    end_line = end_line or line
    end_column = end_column or column
    if column < 1:
        column = 1
    if end_column < 1:
        end_column = 1
    if end_line < line:
        end_line = line
    if snippet is None:
        snippet = line_snippet(parsed.lines, line, end_line)
    severity = rule.severity
    severity_for = getattr(ctx, "severity_for", None)
    if callable(severity_for):
        severity = severity_for(rule)
    return Finding(
        rule_id=rule.id,
        rule_name=rule.name,
        severity=severity,
        message=message,
        path=parsed.path,
        line=line,
        column=column,
        end_line=end_line,
        end_column=max(end_column, column),
        hint=rule.hint,
        snippet=snippet,
    )


def walk_skip_nested(node: ast.AST) -> Iterator[ast.AST]:
    """Yield ``node`` and descendants, skipping nested functions and classes."""
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield from walk_skip_nested(child)


def iter_functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def ancestors(parents: dict[int, ast.AST], node: ast.AST) -> Iterator[ast.AST]:
    current = parents.get(id(node))
    while current is not None:
        yield current
        current = parents.get(id(current))


def enclosing_function(
    parents: dict[int, ast.AST], node: ast.AST
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for current in ancestors(parents, node):
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
    return None


def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def decorator_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return [decorator_name(item) for item in fn.decorator_list]


def body_without_docstring(
    fn: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module,
) -> list[ast.stmt]:
    body = list(getattr(fn, "body", []))
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def exception_names(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Tuple):
        names: set[str] = set()
        for elt in node.elts:
            names |= exception_names(elt)
        return names
    return set()


def is_broad_handler(handler: ast.ExceptHandler) -> bool:
    names = exception_names(handler.type)
    return bool(names & {"Exception", "BaseException"})


def is_none_or_false(value: ast.AST | None) -> bool:
    if value is None:
        return True
    return isinstance(value, ast.Constant) and value.value in (None, False)


def is_swallow_stmt(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, (ast.Continue, ast.Break)):
        return True
    if (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is Ellipsis
    ):
        return True
    if isinstance(stmt, ast.Return):
        return is_none_or_false(stmt.value)
    return False


def is_swallow_body(body: list[ast.stmt]) -> bool:
    return bool(body) and all(is_swallow_stmt(stmt) for stmt in body)


def handler_reraises(handler: ast.ExceptHandler) -> bool:
    return any(isinstance(node, ast.Raise) for node in walk_skip_nested(handler))


def in_type_checking(parents: dict[int, ast.AST], node: ast.AST) -> bool:
    for current in ancestors(parents, node):
        if isinstance(current, ast.If) and _test_is_type_checking(current.test):
            return True
    return False


def _test_is_type_checking(test: ast.AST) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def in_protocol(parents: dict[int, ast.AST], node: ast.AST) -> bool:
    for current in ancestors(parents, node):
        if isinstance(current, ast.ClassDef) and any(_is_protocol(base) for base in current.bases):
            return True
    return False


def _is_protocol(base: ast.AST) -> bool:
    if isinstance(base, ast.Name):
        return base.id == "Protocol"
    if isinstance(base, ast.Attribute):
        return base.attr == "Protocol"
    return False


def is_abstract_or_overload(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    skip = {"abstractmethod", "abstractproperty", "overload", "override"}
    return any(name in skip for name in decorator_names(fn))


def unparse(node: ast.AST) -> str:
    try:
        rendered = ast.unparse(node)
    except (ValueError, TypeError):
        rendered = "<expr>"
    return rendered


def catches_import_error(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    for current in ancestors(parents, node):
        if not isinstance(current, TRY_TYPES):
            continue
        for handler in current.handlers:
            if handler.type is None:
                return True
            names = exception_names(handler.type)
            if names & {"ImportError", "ModuleNotFoundError"}:
                return True
    return False
