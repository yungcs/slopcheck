"""Debug leftovers, dead helpers, copies, stubs, essays, and versioned names."""

from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from slopcheck.models import Finding
from slopcheck.parse import ParsedFile
from slopcheck.rules.support import (
    Rule,
    body_without_docstring,
    decorator_name,
    is_abstract_or_overload,
    iter_functions,
    in_protocol,
    in_type_checking,
    make_finding,
)

_DEBUG_TEXT = re.compile(
    r"(?i)^\s*(?:debug|dbg|trace|tracing|todo|fixme|xxx|hack|wtf|asdf|qwer+|checkpoint|"
    r"reached|here!?|foo|bar|baz)\b|\bDEBUG\b|\bFIXME\b|\bXXX\b"
)
_BANNER = re.compile(r"^(?:=|\*){3,}|^---+\s*debug", re.IGNORECASE)
_DUMPS = {"locals", "globals", "vars", "dir"}
_TRACE_MODULES = {"pdb", "ipdb", "pudb", "rpdb"}
_ALWAYS_SUFFIX = re.compile(r"(?i)(?:_v\d+|_fixed|_copy|_backup|_old|_refactored)$")
_ANY_SUFFIX = re.compile(
    r"(?i)(?:_v\d+|_fixed|_copy|_backup|_old|_refactored|_new|_temp|_tmp|_updated|_final|_latest|_working)$"
)
_TODO_RETURNS = {"todo", "not implemented", "fixme", "tbd", "..."}


def _is_self_debug(joined: ast.JoinedStr) -> bool:
    values = joined.values
    for index, part in enumerate(values):
        if index == 0 or not isinstance(part, ast.FormattedValue):
            continue
        previous = values[index - 1]
        if not isinstance(previous, ast.Constant) or not isinstance(previous.value, str):
            continue
        if not str(previous.value).endswith("="):
            continue
        expr = part.value
        if getattr(expr, "lineno", None) != getattr(previous, "lineno", None):
            continue
        start = getattr(expr, "col_offset", -1)
        origin = getattr(previous, "col_offset", 0)
        end = getattr(previous, "end_col_offset", -1)
        if start >= origin and start < end:
            return True
    return False


def _debug_text(node: ast.AST) -> bool:
    chunks: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        chunks.append(node.value)
    elif isinstance(node, ast.JoinedStr):
        text = "".join(
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        )
        chunks.append(text)
    for text in chunks:
        if _DEBUG_TEXT.search(text) or _BANNER.search(text.strip()):
            return True
    return False


def _is_dump(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id in _DUMPS:
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _DUMPS:
        return True
    return False


def _is_print(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name) and func.id == "print":
        return True
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "print"
        and isinstance(func.value, ast.Name)
        and func.value.id == "builtins"
    )


def _is_breakpoint(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name) and func.id == "breakpoint":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "set_trace":
        base = func.value
        return isinstance(base, ast.Name) and base.id in _TRACE_MODULES
    return False


def _debug_reason(call: ast.Call) -> str | None:
    if _is_breakpoint(call):
        return "leftover breakpoint or set_trace()"
    if not _is_print(call):
        return None
    if any(isinstance(node, ast.JoinedStr) and _is_self_debug(node) for node in ast.walk(call)):
        return "leftover debug f-string"
    for arg in call.args:
        if _is_dump(arg):
            return "leftover dump of locals, globals, vars, or dir"
        if _debug_text(arg):
            return "leftover debug print"
    return None


class DebugLeftoverRule(Rule):
    id = "SLP005"
    name = "debug-leftover"
    severity = "warning"
    summary = 'Debug `print`, `f"{var=}"`, `breakpoint()`, or `pdb.set_trace()` left in the file.'
    hint = "Remove the debug call. A normal print of a finished message is left alone."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if not isinstance(node, ast.Call):
                continue
            reason = _debug_reason(node)
            if reason is None:
                continue
            findings.append(make_finding(self, ctx, parsed, reason, node=node))
        return findings


def _private_helper(node: ast.FunctionDef | ast.AsyncFunctionDef, parsed: ParsedFile) -> bool:
    name = node.name
    if not name.startswith("_"):
        return False
    if name.startswith("__") and name.endswith("__"):
        return False
    if node.decorator_list:
        return False
    parent = parsed.parents.get(id(node))
    return not isinstance(parent, ast.ClassDef)


def _name_used(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load):
            return True
        if isinstance(node, ast.Attribute) and node.attr == name:
            return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = node.value
                    if isinstance(value, (ast.List, ast.Tuple)):
                        for elt in value.elts:
                            if isinstance(elt, ast.Constant) and elt.value == name:
                                return True
    return False


class UnusedPrivateRule(Rule):
    id = "SLP006"
    name = "unused-private"
    severity = "warning"
    summary = "Module-level or nested `_helper` that nothing in the file references."
    hint = "Delete the helper, or call it. Methods are skipped; other modules may use them."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in iter_functions(parsed.tree):
            if not _private_helper(node, parsed):
                continue
            if _name_used(parsed.tree, node.name):
                continue
            findings.append(
                make_finding(
                    self,
                    ctx,
                    parsed,
                    f"private function `{node.name}` is never used",
                    node=node,
                )
            )
        return findings


@dataclass
class _FuncInfo:
    name: str
    parsed: ParsedFile
    node: ast.FunctionDef | ast.AsyncFunctionDef
    tokens: list[str]
    line: int


def _tokens(fn: ast.AST) -> list[str]:
    out: list[str] = []

    def walk(node: ast.AST, *, root: bool = False) -> None:
        if not root and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append("Nested")
            return
        out.append(type(node).__name__)
        if isinstance(node, ast.Attribute):
            out.append(node.attr)
        elif isinstance(node, ast.Constant):
            out.append(type(node.value).__name__)
            return
        elif isinstance(node, (ast.Name, ast.arg)):
            return
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(fn, root=True)
    return out


def _span(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    end = fn.end_lineno or fn.lineno
    return end - fn.lineno + 1


class NearDuplicateRule(Rule):
    id = "SLP007"
    name = "near-duplicate"
    severity = "warning"
    summary = "Two functions with almost the same structure."
    hint = "Keep one function and parameterize the difference. Delete the copy."

    def check_project(self, files: list[ParsedFile], ctx: object) -> list[Finding]:
        option_int = getattr(ctx, "option_int")
        option_float = getattr(ctx, "option_float")
        min_lines = option_int("SLP007", "min_lines", 12)
        min_tokens = option_int("SLP007", "min_tokens", 25)
        threshold = option_float("SLP007", "threshold", 0.92)
        infos: list[_FuncInfo] = []
        for parsed in files:
            for node in iter_functions(parsed.tree):
                if _span(node) < min_lines:
                    continue
                tokens = _tokens(node)
                if len(tokens) < min_tokens:
                    continue
                infos.append(
                    _FuncInfo(name=node.name, parsed=parsed, node=node, tokens=tokens, line=node.lineno)
                )
        if len(infos) > 200:
            grouped: dict[Path, list[_FuncInfo]] = {}
            for info in infos:
                grouped.setdefault(info.parsed.path, []).append(info)
            pairs = []
            for group in grouped.values():
                pairs.extend(_pairs(group))
        else:
            pairs = _pairs(infos)
        best: dict[tuple[str, int, str], tuple[float, _FuncInfo, _FuncInfo]] = {}
        for left, right in pairs:
            if _contains(left.node, right.node) or _contains(right.node, left.node):
                continue
            if abs(len(left.tokens) - len(right.tokens)) / max(len(left.tokens), 1) > 0.3:
                continue
            ratio = difflib.SequenceMatcher(a=left.tokens, b=right.tokens).ratio()
            if ratio < threshold:
                continue
            later, earlier = _order(left, right)
            key = (str(later.parsed.path), later.line, later.name)
            current = best.get(key)
            if current is None or ratio > current[0]:
                best[key] = (ratio, earlier, later)
        findings: list[Finding] = []
        for ratio, earlier, later in best.values():
            kind = "duplicate" if ratio >= 0.995 else "near-duplicate"
            findings.append(
                make_finding(
                    self,
                    ctx,
                    later.parsed,
                    f"{kind} of `{earlier.name}` ({ratio:.0%} similar)",
                    node=later.node,
                )
            )
        return findings


def _pairs(infos: list[_FuncInfo]) -> list[tuple[_FuncInfo, _FuncInfo]]:
    found: list[tuple[_FuncInfo, _FuncInfo]] = []
    for index, left in enumerate(infos):
        for right in infos[index + 1 :]:
            found.append((left, right))
    return found


def _contains(outer: ast.AST, inner: ast.AST) -> bool:
    return any(node is inner for node in ast.walk(outer)) and outer is not inner


def _order(left: _FuncInfo, right: _FuncInfo) -> tuple[_FuncInfo, _FuncInfo]:
    left_key = (str(left.parsed.path), left.line, left.name)
    right_key = (str(right.parsed.path), right.line, right.name)
    if left_key <= right_key:
        return right, left
    return left, right


def _raise_name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_stub_stmt(stmt: ast.stmt) -> str | None:
    if isinstance(stmt, ast.Pass):
        return "function body is only pass"
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
        return "function body is only `...`"
    if isinstance(stmt, ast.Raise) and _raise_name(stmt.exc) == "NotImplementedError":
        return "function body only raises NotImplementedError"
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        text = stmt.value.value.strip().lower()
        if text in _TODO_RETURNS or text.startswith("todo"):
            return "function returns a TODO placeholder"
    return None


class PlaceholderStubRule(Rule):
    id = "SLP009"
    name = "placeholder-stub"
    severity = "warning"
    summary = "Body is only `pass`, `...`, `NotImplementedError`, or a TODO return."
    hint = "Implement the function or delete it. Abstract methods and `.pyi` stubs are ignored."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        if parsed.path.suffix == ".pyi":
            return []
        findings: list[Finding] = []
        for node in iter_functions(parsed.tree):
            if is_abstract_or_overload(node):
                continue
            if in_protocol(parsed.parents, node) or in_type_checking(parsed.parents, node):
                continue
            body = body_without_docstring(node)
            if not body:
                message = "function has no implementation"
            elif len(body) == 1:
                message = _is_stub_stmt(body[0]) or ""
                if not message:
                    continue
            else:
                continue
            findings.append(make_finding(self, ctx, parsed, message, node=node))
        return findings


class VerboseDocstringRule(Rule):
    id = "SLP012"
    name = "verbose-docstring"
    severity = "note"
    summary = "Multi-line essay above a one or two statement function."
    hint = "Cut the docstring to one line, or delete it. The body is already shorter than the preface."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        option_int = getattr(ctx, "option_int")
        min_lines = option_int("SLP012", "min_doc_lines", 8)
        max_body = option_int("SLP012", "max_body_statements", 2)
        findings: list[Finding] = []
        for node in iter_functions(parsed.tree):
            doc = ast.get_docstring(node, clean=False)
            if not doc:
                continue
            body = body_without_docstring(node)
            doc_lines = doc.count("\n") + 1
            if len(body) <= max_body and doc_lines >= min_lines:
                findings.append(
                    make_finding(
                        self,
                        ctx,
                        parsed,
                        f"docstring is {doc_lines} lines on a {len(body)}-statement function",
                        node=node,
                    )
                )
        return findings


class VersionedNameRule(Rule):
    id = "SLP013"
    name = "versioned-name"
    severity = "warning"
    summary = "Function or class named `*_v2`, `*_fixed`, `*_copy`, and similar leftovers."
    hint = "Rename it to the real name and delete the previous copy. Suffixes like `_new` are flagged when the base name still exists."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        names: set[str] = set()
        nodes: list[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] = []
        for node in ast.walk(parsed.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
                nodes.append(node)
        findings: list[Finding] = []
        for node in nodes:
            match = _ANY_SUFFIX.search(node.name)
            if match is None:
                continue
            base = node.name[: match.start()]
            if _ALWAYS_SUFFIX.search(node.name) or (base and base in names):
                findings.append(
                    make_finding(
                        self,
                        ctx,
                        parsed,
                        f"`{node.name}` looks like a leftover versioned name",
                        node=node,
                    )
                )
        return findings
