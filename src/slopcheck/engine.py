"""Scan files and produce a report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slopcheck.config import Config, ConfigError, load_config, validate_against_rules
from slopcheck.discover import ScanError, discover_files, discover_root
from slopcheck.globs import matches_any, relative
from slopcheck.ignore import IgnoreMap, build_ignore_map
from slopcheck.models import Finding, ParseError, Report
from slopcheck.parse import parse_source, read_source
from slopcheck.resolver import ImportResolver
from slopcheck.rules import RULES
from slopcheck.score import compute_score
from slopcheck.version import __version__


@dataclass
class Context:
    """Per-scan inputs a rule can read."""

    config: Config
    root: Path
    resolver: ImportResolver

    def option(self, rule_id: str, key: str, default: object) -> object:
        options = self.config.rule_options.get(rule_id, {})
        if key in options:
            return options[key]
        hyphen = key.replace("_", "-")
        if hyphen in options:
            return options[hyphen]
        return default

    def option_int(self, rule_id: str, key: str, default: int) -> int:
        value = self.option(rule_id, key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{rule_id}.{key} must be an integer")
        return value

    def option_float(self, rule_id: str, key: str, default: float) -> float:
        value = self.option(rule_id, key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{rule_id}.{key} must be a number")
        return float(value)

    def severity_for(self, rule: object) -> str:
        rule_id = getattr(rule, "id", "")
        default = getattr(rule, "severity", "warning")
        return self.config.severity.get(rule_id, default)


def _allowed_modules(config: Config) -> set[str]:
    raw = config.rule_options.get("SLP010", {}).get("allowed_modules", [])
    if isinstance(raw, str):
        return {part.strip() for part in raw.split(",") if part.strip()}
    if isinstance(raw, list):
        return {str(item).strip() for item in raw if str(item).strip()}
    return set()


def _ignored(finding: Finding, ignore_map: IgnoreMap | None, config: Config, root: Path) -> bool:
    if ignore_map is not None and ignore_map.ignores(finding.line, finding.rule_id, finding.end_line):
        return True
    rel = relative(finding.path, root)
    for pattern, ids in config.per_file_ignores.items():
        if (finding.rule_id in ids or "*" in ids) and matches_any(rel, [pattern]):
            return True
    return False


def exit_code(report: Report, *, min_score: int | None, exit_zero: bool = False) -> int:
    """1 when the scan should fail a check, else 0."""
    if exit_zero:
        return 0
    if report.parse_errors:
        return 1
    if any(item.severity in {"error", "warning"} for item in report.findings):
        return 1
    if min_score is not None and report.score < min_score:
        return 1
    return 0


def scan(
    paths: list[Path | str] | None = None,
    *,
    config: Config | None = None,
    root: Path | str | None = None,
    no_config: bool = False,
    config_path: Path | str | None = None,
) -> Report:
    """Scan Python files and return a report. Higher scores are cleaner."""
    targets = [Path(path) for path in paths] if paths else [Path(".")]
    missing = [target for target in targets if not target.exists()]
    if missing:
        raise FileNotFoundError(missing[0])

    discovered_root, discovered_pyproject = discover_root(targets[0])
    project_root = Path(root) if root is not None else discovered_root
    if config is None:
        if no_config:
            config = Config()
        elif config_path is not None:
            config = load_config(Path(config_path))
        else:
            config = load_config(discovered_pyproject)

    validate_against_rules(config, [rule.id for rule in RULES])
    files = discover_files(targets, project_root, config)
    rule_ids = {rule.id for rule in RULES}
    parsed_files = []
    parse_errors: list[ParseError] = []
    ignore_maps: dict[Path, IgnoreMap] = {}

    for path in files:
        source = ""
        try:
            source = read_source(path)
            parsed = parse_source(path, source)
        except SyntaxError as exc:
            parse_errors.append(
                ParseError(
                    path=path,
                    line=exc.lineno or 1,
                    column=exc.offset or 1,
                    message=exc.msg,
                    line_count=len(source.splitlines()) if source else 0,
                )
            )
            continue
        except (OSError, UnicodeError) as exc:
            parse_errors.append(
                ParseError(path=path, line=1, column=1, message=str(exc), line_count=0)
            )
            continue
        parsed_files.append(parsed)
        ignore_maps[parsed.path.resolve()] = build_ignore_map(parsed.source, rule_ids)

    resolver = ImportResolver(project_root, allowed=_allowed_modules(config))
    ctx = Context(config=config, root=project_root, resolver=resolver)
    enabled = [rule for rule in RULES if config.rule_enabled(rule.id)]
    findings: list[Finding] = []

    def keep(finding: Finding) -> bool:
        ignore_map = ignore_maps.get(finding.path.resolve())
        return not _ignored(finding, ignore_map, config, project_root)

    for rule in enabled:
        for parsed in parsed_files:
            for finding in rule.check_file(parsed, ctx):
                if keep(finding):
                    findings.append(finding)
        for finding in rule.check_project(parsed_files, ctx):
            if keep(finding):
                findings.append(finding)

    deduped: list[Finding] = []
    seen: set[tuple[str, str, int, int, str]] = set()
    for finding in findings:
        key = (finding.rule_id, str(finding.path.resolve()), finding.line, finding.column, finding.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    deduped.sort(key=lambda item: (relative(item.path, project_root), item.line, item.column, item.rule_id))

    lines = sum(parsed.line_count for parsed in parsed_files)
    lines += sum(error.line_count for error in parse_errors)
    scored = compute_score(deduped, lines)
    return Report(
        findings=deduped,
        parse_errors=parse_errors,
        files_scanned=len(parsed_files) + len(parse_errors),
        lines_scanned=lines,
        score=scored.value,
        label=scored.label,
        raw=scored.raw,
        budget=scored.budget,
        version=__version__,
        root=project_root,
        warnings=list(config.warnings),
    )


__all__ = ["Context", "ScanError", "exit_code", "scan"]
