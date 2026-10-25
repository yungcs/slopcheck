"""Load ``[tool.slopcheck]`` from a TOML file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """The config file is missing a usable shape."""


@dataclass
class Config:
    """Resolved slopcheck settings."""

    exclude: list[str] = field(default_factory=list)
    select: list[str] | None = None
    ignore: list[str] = field(default_factory=list)
    per_file_ignores: dict[str, list[str]] = field(default_factory=dict)
    severity: dict[str, str] = field(default_factory=dict)
    rule_options: dict[str, dict[str, Any]] = field(default_factory=dict)
    min_score: int | None = None
    warnings: list[str] = field(default_factory=list)

    def rule_enabled(self, rule_id: str) -> bool:
        """True when select/ignore allow this rule to run."""
        ignored = {item.upper() for item in self.ignore}
        if rule_id.upper() in ignored:
            return False
        if not self.select:
            return True
        selected = [item.upper() for item in self.select]
        upper = rule_id.upper()
        return any(upper == item or upper.startswith(item) for item in selected)


_KNOWN = {
    "exclude",
    "select",
    "ignore",
    "per_file_ignores",
    "severity",
    "rules",
    "min_score",
}
_SEVERITIES = {"error", "warning", "note"}


def _norm(key: str) -> str:
    return key.replace("-", "_")


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    try:
        with path.open("rb") as handle:
            loaded = tomllib.load(handle)
    except OSError as exc:
        raise ConfigError(f"could not read config {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"could not parse config {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"config root must be a table: {path}")
    return loaded


def _as_str_list(value: Any, key: str) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        items: list[str] = []
        for part in value:
            text = str(part).strip()
            if text:
                items.append(text)
        return items
    raise ConfigError(f"{key} must be a list of strings")


def _config_from_table(table: dict[str, Any]) -> Config:
    normalized = {_norm(str(key)): value for key, value in table.items()}
    warnings: list[str] = []
    for key in normalized:
        if key not in _KNOWN:
            warnings.append(f"unknown config key '{key}'")

    exclude = _as_str_list(normalized.get("exclude", []), "exclude")
    select = None
    if "select" in normalized:
        select = [item.upper() for item in _as_str_list(normalized["select"], "select")]
    ignore = [item.upper() for item in _as_str_list(normalized.get("ignore", []), "ignore")]

    per_file_raw = normalized.get("per_file_ignores") or {}
    if not isinstance(per_file_raw, dict):
        raise ConfigError("per-file-ignores must be a table of glob to rule list")
    per_file: dict[str, list[str]] = {}
    for pattern, rules in per_file_raw.items():
        per_file[str(pattern)] = [
            item.upper() for item in _as_str_list(rules, f"per-file-ignores.{pattern}")
        ]

    severity_raw = normalized.get("severity") or {}
    if not isinstance(severity_raw, dict):
        raise ConfigError("severity must be a table of rule id to level")
    severity: dict[str, str] = {}
    for rule_id, level in severity_raw.items():
        text = str(level).lower()
        if text not in _SEVERITIES:
            raise ConfigError(f"severity for {rule_id} must be error, warning, or note")
        severity[str(rule_id).upper()] = text

    rules_raw = normalized.get("rules") or {}
    if not isinstance(rules_raw, dict):
        raise ConfigError("rules must be a table")
    options: dict[str, dict[str, Any]] = {}
    for rule_id, value in rules_raw.items():
        if not isinstance(value, dict):
            raise ConfigError(f"rules.{rule_id} must be a table")
        options[str(rule_id).upper()] = {_norm(str(key)): item for key, item in value.items()}

    min_score = None
    if "min_score" in normalized and normalized["min_score"] is not None:
        value = normalized["min_score"]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError("min-score must be an integer")
        if value < 0 or value > 100:
            raise ConfigError("min-score must be between 0 and 100")
        min_score = value

    return Config(
        exclude=exclude,
        select=select,
        ignore=ignore,
        per_file_ignores=per_file,
        severity=severity,
        rule_options=options,
        min_score=min_score,
        warnings=warnings,
    )


def load_config(path: Path | None) -> Config:
    """Load slopcheck settings from ``pyproject.toml`` or a standalone TOML file."""
    if path is None or not path.is_file():
        return Config()
    data = _read_toml(path)
    if path.name == "pyproject.toml":
        tool = data.get("tool", {})
        if tool is None:
            tool = {}
        if not isinstance(tool, dict):
            raise ConfigError("tool must be a table")
        table = tool.get("slopcheck", {}) or {}
    elif isinstance(data.get("tool"), dict) and isinstance(data["tool"].get("slopcheck"), dict):
        table = data["tool"]["slopcheck"]
    else:
        table = data
    if not isinstance(table, dict):
        raise ConfigError("tool.slopcheck must be a table")
    return _config_from_table(table)


def validate_against_rules(config: Config, rule_ids: list[str]) -> None:
    """Append warnings for select/ignore/severity keys that name no rule."""
    known = set(rule_ids)

    def warn(message: str) -> None:
        if message not in config.warnings:
            config.warnings.append(message)

    for token in config.ignore:
        if token not in known:
            warn(f"ignore lists unknown rule {token}")
    if config.select:
        for token in config.select:
            if not any(rule_id == token or rule_id.startswith(token) for rule_id in rule_ids):
                warn(f"select lists unknown rule prefix {token}")
    for rule_id in config.severity:
        if rule_id not in known:
            warn(f"severity override for unknown rule {rule_id}")
    for rule_id in config.rule_options:
        if rule_id not in known:
            warn(f"options for unknown rule {rule_id}")
