"""Terminal report."""

from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.text import Text

from slopcheck.globs import relative
from slopcheck.models import Report
from slopcheck.score import score_bar

_SEVERITY = {"error": "red", "warning": "yellow", "note": "cyan"}


def _score_style(score: int) -> str:
    if score >= 90:
        return "green"
    if score >= 75:
        return "green3"
    if score >= 50:
        return "yellow"
    if score >= 25:
        return "dark_orange"
    return "red"


def render_text(
    report: Report,
    console: Console,
    *,
    quiet: bool = False,
    snippets: bool = True,
    verbose: bool = False,
    min_score: int | None = None,
) -> None:
    """Print a report. ``quiet`` is one line per finding."""
    if quiet:
        _render_quiet(report, console)
        return

    title = Text()
    title.append("slopcheck", style="bold")
    title.append(f"  {report.version}", style="dim")
    console.print(title)
    console.print(
        f"scanned {report.files_scanned} files · {report.lines_scanned} lines · "
        f"{report.finding_count} findings",
        highlight=False,
    )
    style = _score_style(report.score)
    score = Text()
    score.append("score  ")
    score.append(f"{report.score:>3}", style=f"bold {style}")
    score.append(" / 100  ")
    score.append(score_bar(report.score), style=style)
    score.append(f"  {report.label}", style="dim")
    console.print(score)

    if report.parse_errors:
        console.print()
        for error in report.parse_errors:
            line = Text()
            line.append(relative(error.path, report.root), style="bold red")
            line.append(f":{error.line}:{error.column} ", style="red")
            line.append(error.message, style="red")
            console.print(line, highlight=False)

    grouped: dict[str, list] = {}
    for finding in report.findings:
        grouped.setdefault(relative(finding.path, report.root), []).append(finding)

    for path, findings in grouped.items():
        console.print()
        console.print(Text(path, style="bold"))
        for finding in findings:
            line = Text()
            line.append(f"  {finding.line}:{finding.column}  ", style="dim")
            line.append(f"{finding.rule_id}  ", style="bold")
            line.append(f"{finding.severity:<7}  ", style=_SEVERITY.get(finding.severity, "white"))
            line.append(finding.message)
            console.print(line, highlight=False)
            if snippets and finding.snippet:
                limit = 3 if verbose else 2
                for snippet_line in finding.snippet.splitlines()[:limit]:
                    console.print(Text("        " + snippet_line, style="dim"), highlight=False)
            if verbose and finding.hint:
                console.print(Text("        " + finding.hint, style="italic dim"), highlight=False)

    console.print()
    if not report.findings and not report.parse_errors:
        console.print("no slop found", style="green")
    else:
        counts = Counter(item.rule_id for item in report.findings)
        if counts:
            console.print(
                "  ".join(f"{rule_id} {count}" for rule_id, count in sorted(counts.items())),
                style="dim",
                highlight=False,
            )
    status = _status(report, min_score)
    console.print(
        f"{report.finding_count} findings · score {report.score} · {status}",
        style="bold red" if status == "fail" else "bold green",
        highlight=False,
    )


def _status(report: Report, min_score: int | None) -> str:
    if report.parse_errors:
        return "fail"
    if any(item.severity in {"error", "warning"} for item in report.findings):
        return "fail"
    if min_score is not None and report.score < min_score:
        return "fail"
    return "pass"


def _render_quiet(report: Report, console: Console) -> None:
    for error in report.parse_errors:
        console.print(
            f"{relative(error.path, report.root)}:{error.line}:{error.column}: "
            f"syntax error: {error.message}",
            highlight=False,
            markup=False,
        )
    for finding in report.findings:
        console.print(
            f"{relative(finding.path, report.root)}:{finding.line}:{finding.column}: "
            f"{finding.rule_id} {finding.message}",
            highlight=False,
            markup=False,
        )
    console.print(f"score {report.score} {report.label}", highlight=False, markup=False)
