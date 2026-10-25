"""Shields-style SVG score badge with inline colors."""

from __future__ import annotations

import html


def badge_color(score: int) -> str:
    """Badge color for a score."""
    if score >= 90:
        return "#2da44e"
    if score >= 75:
        return "#5c940d"
    if score >= 50:
        return "#c69026"
    if score >= 25:
        return "#d9480f"
    return "#c92a2a"


def badge_svg(score: int, label: str = "slop") -> str:
    """Return a self-contained SVG badge."""
    score = max(0, min(100, int(score)))
    safe_label = html.escape(label)
    value = str(score)
    left = 10 + 7 * len(label)
    right = 14 + 7 * len(value)
    width = left + right
    color = badge_color(score)
    label_x = left / 2
    value_x = left + right / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" '
        f'role="img" aria-label="{safe_label}: {value}">\n'
        f"  <title>{safe_label}: {value}</title>\n"
        f'  <clipPath id="r"><rect width="{width}" height="20" rx="3" fill="#fff"/></clipPath>\n'
        f'  <g clip-path="url(#r)">\n'
        f'    <rect width="{left}" height="20" fill="#3f3f3f"/>\n'
        f'    <rect x="{left}" width="{right}" height="20" fill="{color}"/>\n'
        f"  </g>\n"
        f'  <g fill="#fff" text-anchor="middle" '
        f'font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">\n'
        f'    <text x="{label_x:.1f}" y="14">{safe_label}</text>\n'
        f'    <text x="{value_x:.1f}" y="14">{value}</text>\n'
        f"  </g>\n"
        f"</svg>\n"
    )
