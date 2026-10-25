"""Command line interface."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from slopcheck.config import ConfigError
from slopcheck.discover import ScanError
from slopcheck.engine import exit_code
from slopcheck.engine import scan as scan_paths
from slopcheck.formatters.badge import badge_svg
from slopcheck.formatters.html import render_html
from slopcheck.formatters.jsonfmt import render_json
from slopcheck.formatters.prompt import render_prompt
from slopcheck.formatters.sarif import render_sarif
from slopcheck.formatters.text import render_text
from slopcheck.rules import RULES
from slopcheck.version import __version__

app = typer.Typer(
    name="slopcheck",
    help="A linter for the mess AI coding agents leave in Python.",
    invoke_without_command=True,
    no_args_is_help=False,
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
)
FORMATS = {"text", "json", "sarif", "html", "badge", "prompt"}
_COMMANDS = {"scan", "rules", "prompt", "badge"}


def prepare_argv(argv: list[str]) -> list[str]:
    """Insert the scan command when the user passed paths or scan flags."""
    if not argv:
        return ["scan"]
    for arg in argv:
        if arg in _COMMANDS or arg in {"-h", "--help", "--version"}:
            return list(argv)
        if arg.startswith("-"):
            continue
        return ["scan", *argv]
    return ["scan", *argv]


def cli(argv: list[str] | None = None) -> None:
    """Console-script entry point."""
    args = prepare_argv(list(sys.argv[1:] if argv is None else argv))
    app(args=args, prog_name="slopcheck")


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().upper() for part in value.split(",") if part.strip()]


def _write(text: str, output: Path | None) -> None:
    if output is None or str(output) == "-":
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _fail(message: str, code: int = 2) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code)


def _emit(
    targets: list[Path],
    *,
    format: str,
    output: Path | None,
    select: str | None,
    ignore: str | None,
    config: Path | None,
    no_config: bool,
    min_score: int | None,
    exit_zero: bool,
    quiet: bool,
    no_color: bool,
    no_snippet: bool,
    verbose: bool,
) -> None:
    from dataclasses import replace

    from slopcheck.config import Config, load_config
    from slopcheck.discover import discover_root

    discovered_root, discovered_pyproject = discover_root(targets[0] if targets[0].exists() else Path.cwd())
    if no_config:
        loaded = Config()
    elif config is not None:
        loaded = load_config(config)
    else:
        loaded = load_config(discovered_pyproject)
    if select:
        loaded = replace(loaded, select=_csv(select))
    if ignore:
        loaded = replace(loaded, ignore=[*loaded.ignore, *_csv(ignore)])
    if min_score is not None and (min_score < 0 or min_score > 100):
        _fail("min-score must be between 0 and 100")
    try:
        report = scan_paths(targets, config=loaded, root=discovered_root)
    except ConfigError as exc:
        _fail(str(exc))
    except ScanError as exc:
        _fail(str(exc))
    except FileNotFoundError as exc:
        _fail(f"path not found: {exc}")

    for warning in report.warnings:
        typer.echo(f"warning: {warning}", err=True)

    effective_min = min_score if min_score is not None else loaded.min_score
    if format == "text":
        snippets = not no_snippet and not quiet
        if output is None:
            console = Console(no_color=no_color, highlight=False)
            render_text(
                report,
                console,
                quiet=quiet,
                snippets=snippets,
                verbose=verbose,
                min_score=effective_min,
            )
        else:
            buffer = io.StringIO()
            console = Console(
                file=buffer,
                force_terminal=False,
                no_color=True,
                highlight=False,
                width=100,
            )
            render_text(
                report,
                console,
                quiet=quiet,
                snippets=snippets,
                verbose=verbose,
                min_score=effective_min,
            )
            _write(buffer.getvalue(), output)
    else:
        rendered = {
            "json": render_json,
            "sarif": render_sarif,
            "html": render_html,
            "badge": lambda item: badge_svg(item.score),
            "prompt": render_prompt,
        }[format](report)
        _write(rendered, output)
    raise typer.Exit(exit_code(report, min_score=effective_min, exit_zero=exit_zero))


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show the version and exit."),
) -> None:
    """A linter for the mess AI coding agents leave in Python.

    Examples:

      slopcheck .

      slopcheck src --format sarif -o slopcheck.sarif

      slopcheck prompt . > fix.md

      slopcheck --fix-with-agent src/app.py
    """
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def scan(
    paths: list[Path] | None = typer.Argument(None, help="Files or directories. Defaults to the current directory."),
    format: str = typer.Option("text", "--format", "-f", help="text, json, sarif, html, badge, or prompt."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write the report to this file."),
    select: str | None = typer.Option(None, "--select", help="Comma-separated rule ids or prefixes to enable."),
    ignore: str | None = typer.Option(None, "--ignore", help="Comma-separated rule ids to disable."),
    config: Path | None = typer.Option(None, "--config", help="TOML config file."),
    no_config: bool = typer.Option(False, "--no-config", help="Ignore project configuration."),
    min_score: int | None = typer.Option(None, "--min-score", help="Also fail when the score is below this."),
    exit_zero: bool = typer.Option(False, "--exit-zero", help="Always exit 0. Useful when you only want the report."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="One line per finding, plus the score."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color."),
    no_snippet: bool = typer.Option(False, "--no-snippet", help="Omit code snippets."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show hints and a longer snippet."),
    fix_with_agent: bool = typer.Option(
        False,
        "--fix-with-agent",
        help="Print a fix prompt for Claude Code, Codex, or Cursor.",
    ),
) -> None:
    """Scan Python files and print a Slop Score. Higher is cleaner."""
    if format not in FORMATS:
        _fail(f"unknown format {format!r}")
    _emit(
        list(paths) if paths else [Path(".")],
        format="prompt" if fix_with_agent else format,
        output=output,
        select=select,
        ignore=ignore,
        config=config,
        no_config=no_config,
        min_score=min_score,
        exit_zero=exit_zero,
        quiet=quiet,
        no_color=no_color,
        no_snippet=no_snippet,
        verbose=verbose,
    )


@app.command()
def prompt(
    paths: list[Path] | None = typer.Argument(None, help="Files or directories. Defaults to the current directory."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write the prompt to this file."),
    select: str | None = typer.Option(None, "--select", help="Comma-separated rule ids or prefixes to enable."),
    ignore: str | None = typer.Option(None, "--ignore", help="Comma-separated rule ids to disable."),
    config: Path | None = typer.Option(None, "--config", help="TOML config file."),
    no_config: bool = typer.Option(False, "--no-config", help="Ignore project configuration."),
) -> None:
    """Write a fix prompt for Claude Code, Codex, or Cursor."""
    _emit(
        list(paths) if paths else [Path(".")],
        format="prompt",
        output=output,
        select=select,
        ignore=ignore,
        config=config,
        no_config=no_config,
        min_score=None,
        exit_zero=False,
        quiet=False,
        no_color=True,
        no_snippet=False,
        verbose=False,
    )


@app.command()
def rules(
    format: str = typer.Option("text", "--format", "-f", help="text or json."),
) -> None:
    """List rules."""
    if format == "json":
        payload = [
            {
                "id": rule.id,
                "name": rule.name,
                "severity": rule.severity,
                "summary": rule.summary,
                "hint": rule.hint,
            }
            for rule in RULES
        ]
        typer.echo(json.dumps(payload, indent=2))
        return
    if format != "text":
        _fail("rules --format must be text or json")
    table = Table(title="slopcheck rules", header_style="bold")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Sev")
    table.add_column("Summary")
    for rule in RULES:
        table.add_row(rule.id, rule.name, rule.severity, rule.summary)
    Console().print(table)


@app.command()
def badge(
    paths: list[Path] | None = typer.Argument(None, help="Scan these paths. Omit when passing --score."),
    score: int | None = typer.Option(None, "--score", min=0, max=100, help="Render this score instead of scanning."),
    output: Path = typer.Option(Path("slop-score.svg"), "--output", "-o", help="Badge path."),
    label: str = typer.Option("slop", "--label", help="Left-hand badge label."),
    no_config: bool = typer.Option(False, "--no-config", help="Ignore project configuration."),
) -> None:
    """Write an SVG score badge."""
    if score is not None:
        _write(badge_svg(score, label=label), output)
        return
    from slopcheck.config import Config, load_config
    from slopcheck.discover import discover_root

    targets = list(paths) if paths else [Path(".")]
    if not targets[0].exists():
        _fail(f"path not found: {targets[0]}")
    _root, pyproject = discover_root(targets[0])
    loaded = Config() if no_config else load_config(pyproject)
    try:
        report = scan_paths(targets, config=loaded, root=_root)
    except (ConfigError, ScanError, FileNotFoundError) as exc:
        _fail(str(exc))
    _write(badge_svg(report.score, label=label), output)
    effective = None if no_config else loaded.min_score
    raise typer.Exit(exit_code(report, min_score=effective, exit_zero=False))
