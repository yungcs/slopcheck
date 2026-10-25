"""None and isinstance checks that cannot fail."""

from __future__ import annotations

import ast

from slopcheck.models import Finding
from slopcheck.parse import ParsedFile
from slopcheck.rules.support import TRY_TYPES, Rule, make_finding, walk_skip_nested


def _literal_kind(value: ast.AST) -> str | None:
    if isinstance(value, ast.Constant):
        raw = value.value
        if raw is None:
            return None
        if isinstance(raw, bool):
            return "bool"
        if isinstance(raw, str):
            return "str"
        if isinstance(raw, int):
            return "int"
        if isinstance(raw, float):
            return "float"
        if isinstance(raw, bytes):
            return "bytes"
        return None
    if isinstance(value, ast.List):
        return "list"
    if isinstance(value, ast.Dict):
        return "dict"
    if isinstance(value, ast.Tuple):
        return "tuple"
    if isinstance(value, ast.Set):
        return "set"
    return None


def _none_checks(test: ast.AST) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    class Visitor(ast.NodeVisitor):
        def visit_Compare(self, node: ast.Compare) -> None:
            if (
                isinstance(node.left, ast.Name)
                and len(node.ops) == 1
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value is None
            ):
                if isinstance(node.ops[0], (ast.Is, ast.Eq)):
                    found.append((node.left.id, "none"))
                elif isinstance(node.ops[0], (ast.IsNot, ast.NotEq)):
                    found.append((node.left.id, "not_none"))
            self.generic_visit(node)

    Visitor().visit(test)
    return found


def _isinstance_object(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or len(node.args) != 2:
        return False
    if not isinstance(node.func, ast.Name) or node.func.id != "isinstance":
        return False
    second = node.args[1]
    if isinstance(second, ast.Name) and second.id == "object":
        return True
    if isinstance(second, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id == "object" for elt in second.elts)
    return False


def _isinstance_pairs(test: ast.AST) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for node in ast.walk(test):
        if not isinstance(node, ast.Call) or len(node.args) != 2:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "isinstance":
            continue
        if isinstance(node.args[0], ast.Name) and isinstance(node.args[1], ast.Name):
            pairs.append((node.args[0].id, node.args[1].id))
    return pairs


def _simple_none(test: ast.AST) -> tuple[str, str] | None:
    if not isinstance(test, ast.Compare):
        return None
    checks = _none_checks(test)
    if len(checks) != 1:
        return None
    name, polarity = checks[0]
    return polarity, name


def _always_returns(stmts: list[ast.stmt]) -> bool:
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise)):
        return True
    if isinstance(last, ast.If):
        return _always_returns(last.body) and _always_returns(last.orelse)
    return False


def _assigned_names(stmt: ast.AST) -> set[str]:
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return set()
    names: set[str] = set()
    for node in walk_skip_nested(stmt):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return names


class OverDefensiveRule(Rule):
    id = "SLP008"
    name = "over-defensive"
    severity = "note"
    summary = "A None or isinstance check that cannot fail given the code just above it."
    hint = "Delete the branch. Checks on parameters and on values returned from calls are kept."

    def check_file(self, parsed: ParsedFile, ctx: object) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(parsed.tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                _analyze_block(list(node.body), {}, set(), findings, parsed, ctx, self)
        return findings


def _flag_test(
    test: ast.AST,
    literal: dict[str, str],
    proven: set[str],
    stmt: ast.stmt,
    findings: list[Finding],
    parsed: ParsedFile,
    ctx: object,
    rule: Rule,
) -> None:
    reasons: list[str] = []
    checks = _none_checks(test)
    if len(checks) != len(set(checks)):
        reasons.append("repeats a None check")
    if any(_isinstance_object(node) for node in ast.walk(test)):
        reasons.append("`isinstance(..., object)` is always true for instances")
    seen: set[str] = set()
    for name, _polarity in checks:
        if name in seen:
            continue
        seen.add(name)
        if name in literal:
            reasons.append(f"`{name}` is a non-None literal here")
        elif name in proven:
            reasons.append(f"`{name}` was already checked for None")
    for name, type_name in _isinstance_pairs(test):
        if literal.get(name) == type_name:
            reasons.append(f"`{name}` was just assigned as {type_name}")
    if not reasons:
        return
    unique: list[str] = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    findings.append(
        make_finding(
            rule,
            ctx,
            parsed,
            "over-defensive check: " + "; ".join(unique),
            node=stmt,
        )
    )


def _remember_assign(name: str, value: ast.AST, literal: dict[str, str], proven: set[str]) -> None:
    proven.discard(name)
    kind = _literal_kind(value)
    if kind is None:
        literal.pop(name, None)
    else:
        literal[name] = kind


def _analyze_block(
    stmts: list[ast.stmt],
    literal: dict[str, str],
    proven: set[str],
    findings: list[Finding],
    parsed: ParsedFile,
    ctx: object,
    rule: Rule,
) -> None:
    literal = dict(literal)
    proven = set(proven)
    for stmt in stmts:
        if isinstance(stmt, ast.If):
            _flag_test(stmt.test, literal, proven, stmt, findings, parsed, ctx, rule)
            inside = _assigned_names(stmt)
            body_proven = set(proven)
            else_proven = set(proven)
            simple = _simple_none(stmt.test)
            if simple is not None and simple[0] == "none":
                else_proven.add(simple[1])
            elif simple is not None and simple[0] == "not_none":
                body_proven.add(simple[1])
            elif isinstance(stmt.test, ast.BoolOp) and isinstance(stmt.test.op, ast.And):
                for name, polarity in _none_checks(stmt.test):
                    if polarity == "not_none":
                        body_proven.add(name)
            _analyze_block(stmt.body, literal, body_proven, findings, parsed, ctx, rule)
            _analyze_block(stmt.orelse, literal, else_proven, findings, parsed, ctx, rule)
            for name in inside:
                literal.pop(name, None)
                proven.discard(name)
            if (
                simple is not None
                and simple[0] == "none"
                and _always_returns(stmt.body)
                and simple[1] not in inside
            ):
                proven.add(simple[1])
        elif isinstance(stmt, ast.While):
            _flag_test(stmt.test, literal, proven, stmt, findings, parsed, ctx, rule)
            _analyze_block(stmt.body, {}, set(), findings, parsed, ctx, rule)
            _analyze_block(stmt.orelse, {}, set(), findings, parsed, ctx, rule)
            for name in _assigned_names(stmt):
                literal.pop(name, None)
                proven.discard(name)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            _analyze_block(stmt.body, {}, set(), findings, parsed, ctx, rule)
            _analyze_block(stmt.orelse, {}, set(), findings, parsed, ctx, rule)
            for name in _assigned_names(stmt):
                literal.pop(name, None)
                proven.discard(name)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            _analyze_block(stmt.body, {}, set(), findings, parsed, ctx, rule)
            for name in _assigned_names(stmt):
                literal.pop(name, None)
                proven.discard(name)
        elif isinstance(stmt, TRY_TYPES):
            assigned = _assigned_names(stmt)
            _analyze_block(stmt.body, literal, proven, findings, parsed, ctx, rule)
            for handler in stmt.handlers:
                _analyze_block(handler.body, literal, proven, findings, parsed, ctx, rule)
            _analyze_block(stmt.orelse, literal, proven, findings, parsed, ctx, rule)
            _analyze_block(list(getattr(stmt, "finalbody", [])), literal, proven, findings, parsed, ctx, rule)
            for name in assigned:
                literal.pop(name, None)
                proven.discard(name)
        elif isinstance(stmt, ast.Assign):
            targets: list[str] = []
            simple_targets = True
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    targets.append(target.id)
                else:
                    simple_targets = False
                    break
            if simple_targets and targets:
                for name in targets:
                    _remember_assign(name, stmt.value, literal, proven)
            else:
                for name in _assigned_names(stmt):
                    literal.pop(name, None)
                    proven.discard(name)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if stmt.value is None:
                literal.pop(stmt.target.id, None)
                proven.discard(stmt.target.id)
            else:
                _remember_assign(stmt.target.id, stmt.value, literal, proven)
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            literal.pop(stmt.target.id, None)
            proven.discard(stmt.target.id)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        else:
            for name in _assigned_names(stmt):
                literal.pop(name, None)
                proven.discard(name)
