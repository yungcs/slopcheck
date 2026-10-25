"""Regenerate the README terminal SVG, score badge, and HTML sample."""

from __future__ import annotations

import io
import re
from pathlib import Path

from rich.console import Console

from slopcheck.engine import scan
from slopcheck.formatters.badge import badge_svg
from slopcheck.formatters.html import render_html
from slopcheck.formatters.text import render_text

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WIDTH = 156
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
_STYLE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_RULE = re.compile(r"\.([A-Za-z0-9_-]+)\s*\{([^}]*)\}")
_TAG = re.compile(r"<(?:text|g)\b[^>]*>")


def main() -> None:
    """Write docs/demo.svg, docs/demo.txt, docs/demo-report.html, and the badge."""
    DOCS.mkdir(parents=True, exist_ok=True)
    demo = scan([ROOT / "demo"])
    console = Console(
        file=io.StringIO(),
        record=True,
        width=WIDTH,
        height=40,
        force_terminal=True,
        color_system="standard",
        highlight=False,
    )
    console.print("$ slopcheck demo", style="bold")
    render_text(demo, console)
    svg = inline_svg(console.export_svg(title="slopcheck demo", clear=False))
    _reject_remote(svg)
    (DOCS / "demo.svg").write_text(svg, encoding="utf-8")
    (DOCS / "demo.txt").write_text(console.export_text(clear=False), encoding="utf-8")
    (DOCS / "demo-report.html").write_text(render_html(demo), encoding="utf-8")
    repo = scan([ROOT])
    badge = badge_svg(repo.score)
    _reject_remote(badge)
    (DOCS / "slop-score.svg").write_text(badge, encoding="utf-8")
    print(f"demo score {demo.score} findings {demo.finding_count}")
    print(f"repo score {repo.score}")


def inline_svg(svg: str) -> str:
    """Copy Rich class colors onto fill attributes and drop the style block."""
    classes: dict[str, dict[str, str]] = {}
    for name, body in _RULE.findall(svg):
        classes[name] = _declarations(body)
    svg = _COMMENT.sub("", svg)
    svg = _STYLE.sub("", svg)
    svg = svg.replace(' class="rich-terminal"', "")
    svg = svg.replace('stroke="rgba(255,255,255,0.35)"', 'stroke="#5c5c5c"')
    svg = _TAG.sub(lambda match: _apply(match.group(0), classes), svg)
    return _FLOAT.sub(_round_float, svg)


_FLOAT = re.compile(r"\d+\.\d{3,}")


def _round_float(match: re.Match[str]) -> str:
    text = f"{float(match.group(0)):.2f}"
    return text.rstrip("0").rstrip(".")


def _declarations(body: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for key in ("fill", "font-weight", "font-size", "font-family"):
        match = re.search(rf"{key}:\s*([^;]+)", body)
        if match:
            props[key] = match.group(1).strip()
    family = props.get("font-family", "")
    if family and ("url(" in family or "Fira" in family or family == "arial"):
        props["font-family"] = MONO
    return props


def _apply(tag: str, classes: dict[str, dict[str, str]]) -> str:
    match = re.search(r'class="([^"]+)"', tag)
    if match is None:
        return tag
    props: dict[str, str] = {}
    for name in match.group(1).split():
        props.update(classes.get(name, {}))
    if tag.startswith("<text") or tag.startswith("<g"):
        props.setdefault("font-family", MONO)
    rendered = re.sub(r'\sclass="[^"]*"', "", tag)
    extras = []
    for key, value in props.items():
        if f'{key}="' in rendered:
            continue
        extras.append(f'{key}="{value}"')
    if not extras:
        return rendered
    return rendered[:-1] + " " + " ".join(extras) + ">"


def _reject_remote(svg: str) -> None:
    leftover = svg.replace("http://www.w3.org/2000/svg", "")
    if "<style" in leftover or "http://" in leftover or "https://" in leftover:
        raise RuntimeError("svg still has a style block or a remote url")


if __name__ == "__main__":
    main()
