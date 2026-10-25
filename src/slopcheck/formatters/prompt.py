"""Fix prompt for a coding agent."""

from __future__ import annotations

from slopcheck.globs import relative
from slopcheck.models import Report


def render_prompt(report: Report) -> str:
    """Markdown an agent can paste into Claude Code, Codex, or Cursor."""
    lines = [
        "# Fix the slopcheck findings",
        "",
        "You are cleaning AI-agent residue in Python. Keep behavior the same,",
        "except where a finding is swallowed control flow: those should raise",
        "or handle a specific exception, not disappear.",
        "",
        f"Slop score: **{report.score} / 100** ({report.label}). Target: 90 or better.",
        "",
        "Rules:",
        "- Fix each finding below.",
        "- Do not add narrating comments, broad `except` clauses, debug prints, or dummy fallbacks.",
        "- Do not rename a public function unless the finding is a versioned name and you are sure nothing else imports it. If you are unsure, leave the name and say so.",
        "- Prefer deleting dead code over wrapping it in another guard.",
        "- After editing, run `slopcheck` on the touched files and repair anything new you introduced.",
        "",
    ]
    if report.parse_errors:
        lines.append("## Files that failed to parse")
        lines.append("")
        for error in report.parse_errors:
            rel = relative(error.path, report.root)
            lines.append(f"- `{rel}:{error.line}` {error.message}")
        lines.append("")
    if not report.findings:
        lines.append("No slop findings.")
        lines.append("")
        return "\n".join(lines)

    current = None
    for finding in report.findings:
        rel = relative(finding.path, report.root)
        if rel != current:
            current = rel
            lines.append(f"## {rel}")
            lines.append("")
        lines.append(
            f"### {finding.rule_id} {finding.rule_name} — line {finding.line}:{finding.column}"
        )
        lines.append("")
        lines.append(f"**{finding.severity}.** {finding.message}")
        lines.append("")
        lines.append(finding.hint)
        lines.append("")
        if finding.snippet:
            lines.append("```python")
            lines.append(finding.snippet)
            lines.append("```")
            lines.append("")
    return "\n".join(lines)
