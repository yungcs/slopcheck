"""Render a report to text, JSON, SARIF, HTML, a badge, or a fix prompt."""

from slopcheck.formatters.badge import badge_svg
from slopcheck.formatters.html import render_html
from slopcheck.formatters.jsonfmt import render_json
from slopcheck.formatters.prompt import render_prompt
from slopcheck.formatters.sarif import render_sarif

__all__ = ["badge_svg", "render_html", "render_json", "render_prompt", "render_sarif"]
