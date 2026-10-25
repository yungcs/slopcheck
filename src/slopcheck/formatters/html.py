"""Self-contained HTML report."""

from __future__ import annotations

import html
import json
from collections import Counter

from slopcheck.formatters.jsonfmt import report_dict
from slopcheck.globs import relative
from slopcheck.models import Report
from slopcheck.score import score_bar


def _score_color(score: int) -> str:
    if score >= 90:
        return "#c6f35a"
    if score >= 75:
        return "#9ccc65"
    if score >= 50:
        return "#ffb020"
    if score >= 25:
        return "#ff7a32"
    return "#ff5c39"


def render_html(report: Report) -> str:
    """A single HTML file with inline CSS and no network requests."""
    color = _score_color(report.score)
    counts = Counter(item.rule_id for item in report.findings)
    severity_counts = Counter(item.severity for item in report.findings)
    chips = []
    for rule_id, count in sorted(counts.items()):
        chips.append(
            f'<button type="button" data-filter="{html.escape(rule_id)}">'
            f"{html.escape(rule_id)} {count}</button>"
        )
    articles: list[str] = []
    current = None
    for finding in report.findings:
        rel = relative(finding.path, report.root)
        if rel != current:
            current = rel
            articles.append(f'<h2>{html.escape(rel)}</h2>')
        snippet = (
            f"<pre><code>{html.escape(finding.snippet)}</code></pre>" if finding.snippet else ""
        )
        articles.append(
            "<article "
            f'data-severity="{html.escape(finding.severity)}" '
            f'data-rule="{html.escape(finding.rule_id)}">'
            f'<header><span class="loc">{finding.line}:{finding.column}</span>'
            f'<span class="rule">{html.escape(finding.rule_id)}</span>'
            f'<span class="sev {html.escape(finding.severity)}">{html.escape(finding.severity)}</span>'
            f"<p>{html.escape(finding.message)}</p></header>"
            f"{snippet}"
            f'<p class="hint">{html.escape(finding.hint)}</p>'
            "</article>"
        )
    errors = []
    for error in report.parse_errors:
        rel = relative(error.path, report.root)
        errors.append(
            f"<p class=\"parse\">{html.escape(rel)}:{error.line}:{error.column} "
            f"{html.escape(error.message)}</p>"
        )
    body = "\n".join(articles) if articles else '<p class="clean">No slop found.</p>'
    payload = json.dumps(report_dict(report)).replace("<", "\\u003c").replace(">", "\\u003e")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>slopcheck {report.score}/100</title>
<style>
:root {{
  color-scheme: dark;
  --bg: #10140f;
  --card: #181e16;
  --line: #2c3824;
  --text: #e7ecdf;
  --dim: #9aa892;
  --accent: {color};
  --error: #ff5c39;
  --warning: #ffb020;
  --note: #79d2ff;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
main {{ max-width: 980px; margin: 0 auto; padding: 28px 18px 64px; }}
header.top {{
  display: flex;
  gap: 28px;
  align-items: flex-end;
  justify-content: space-between;
  border-bottom: 1px solid var(--line);
  padding-bottom: 18px;
}}
.word {{ font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--dim); }}
.score {{ font-size: 72px; line-height: 0.9; color: var(--accent); font-weight: 700; }}
.score span {{ font-size: 18px; color: var(--dim); font-weight: 500; }}
.meta {{ color: var(--dim); text-align: right; }}
.bar {{ color: var(--accent); letter-spacing: 1px; }}
.filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }}
button, input {{
  background: var(--card);
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 12px;
  font: inherit;
}}
button[aria-pressed="true"] {{ border-color: var(--accent); color: var(--accent); }}
input {{ border-radius: 8px; min-width: 180px; }}
h2 {{ font-size: 14px; margin: 22px 0 8px; }}
article {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 0 0 10px;
}}
article header {{ display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: baseline; }}
.loc {{ color: var(--dim); }}
.rule {{ font-weight: 700; }}
.sev {{ text-transform: uppercase; font-size: 12px; letter-spacing: 0.06em; }}
.sev.error {{ color: var(--error); }}
.sev.warning {{ color: var(--warning); }}
.sev.note {{ color: var(--note); }}
article p {{ margin: 8px 0 0; }}
pre {{
  margin: 10px 0 0;
  padding: 8px 10px;
  overflow: auto;
  background: #0c100c;
  border-radius: 8px;
  color: #d5dcc8;
}}
.hint {{ color: var(--dim); }}
.parse {{ color: var(--error); }}
.clean {{ color: var(--accent); }}
footer {{ margin-top: 28px; color: var(--dim); }}
@media (max-width: 640px) {{
  header.top {{ flex-direction: column; align-items: flex-start; }}
  .meta {{ text-align: left; }}
  .score {{ font-size: 56px; }}
}}
</style>
</head>
<body>
<main>
  <header class="top">
    <div>
      <div class="word">slopcheck {html.escape(report.version)}</div>
      <div class="score">{report.score}<span> / 100</span></div>
      <div class="bar">{html.escape(score_bar(report.score, 16))} {html.escape(report.label)}</div>
    </div>
    <div class="meta">
      <div>{report.files_scanned} files</div>
      <div>{report.lines_scanned} lines</div>
      <div>{report.finding_count} findings</div>
      <div>{severity_counts.get("error", 0)} errors · {severity_counts.get("warning", 0)} warnings · {severity_counts.get("note", 0)} notes</div>
    </div>
  </header>
  <div class="filters">
    <button type="button" data-filter="all" aria-pressed="true">all</button>
    <button type="button" data-filter="error">errors</button>
    <button type="button" data-filter="warning">warnings</button>
    <button type="button" data-filter="note">notes</button>
    {''.join(chips)}
    <input id="q" type="search" placeholder="filter text" aria-label="filter findings">
  </div>
  {''.join(errors)}
  <section id="findings">
    {body}
  </section>
  <footer>generated by slopcheck {html.escape(report.version)}</footer>
</main>
<script id="report-data" type="application/json">{payload}</script>
<script>
const buttons = document.querySelectorAll("button[data-filter]");
const cards = document.querySelectorAll("#findings article");
const query = document.getElementById("q");
let active = "all";
function apply() {{
  const needle = (query.value || "").toLowerCase();
  cards.forEach((card) => {{
    const sev = card.dataset.severity;
    const rule = card.dataset.rule;
    const text = card.textContent.toLowerCase();
    const byFilter = active === "all" || active === sev || active === rule;
    card.hidden = !(byFilter && (!needle || text.includes(needle)));
  }});
}}
buttons.forEach((button) => {{
  button.addEventListener("click", () => {{
    active = button.dataset.filter;
    buttons.forEach((item) => item.setAttribute("aria-pressed", item === button ? "true" : "false"));
    apply();
  }});
}});
query.addEventListener("input", apply);
</script>
</body>
</html>
"""
