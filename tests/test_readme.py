"""README copy and committed demo assets stay tied to the rule set."""

import os
from pathlib import Path

from slopcheck.rules import RULES

ROOT = Path(__file__).resolve().parents[1]


def test_readmes_name_every_rule():
    transcript = (ROOT / "docs" / "demo.txt").read_text(encoding="utf-8")
    for name in ("README.md", "README.zh-CN.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "uvx slopcheck" in text
        assert "pipx install slopcheck" in text
        assert "20 findings · score 29 · fail" in text
        for rule in RULES:
            assert rule.id in text
            assert rule.id in transcript


def test_demo_assets_are_self_contained():
    svg = (ROOT / "docs" / "demo.svg").read_text(encoding="utf-8")
    assert "<style" not in svg
    assert "https://" not in svg
    assert 'fill="' in svg
    assert "SLP001" in svg
    badge = (ROOT / "docs" / "slop-score.svg").read_text(encoding="utf-8")
    assert ">100<" in badge
    assert "#2da44e" in badge
    assert "<style" not in badge
    html = (ROOT / "docs" / "demo-report.html").read_text(encoding="utf-8")
    assert "slopcheck 29/100" in html
    assert "https://" not in html
    assert 'type="application/json"' in html


def test_launch_visuals_and_metadata():
    from PIL import Image

    docs = ROOT / "docs"
    dark = Image.open(docs / "hero-dark.png")
    light = Image.open(docs / "hero-light.png")
    assert dark.size == light.size == (1600, 560)
    assert dark.tobytes() != light.tobytes()
    assert Image.open(docs / "social-preview.png").size == (1280, 640)
    assert Image.open(docs / "before-after.png").size[0] >= 1200
    assert Image.open(docs / "report.png").size[0] >= 1000
    gif = Image.open(docs / "demo.gif")
    elapsed = 0
    for index in range(gif.n_frames):
        gif.seek(index)
        elapsed += gif.info.get("duration", 0)
    assert 5 < elapsed / 1000 < 15
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "https://github.com/yonguyungcs-pixel/slopcheck" in pyproject
    for name in ("README.md", "README.zh-CN.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for asset in (
            "docs/hero-dark.png",
            "docs/hero-light.png",
            "docs/demo.gif",
            "docs/before-after.png",
            "docs/report.png",
            "docs/slop-score.svg",
        ):
            assert asset in text
        assert "prefers-color-scheme: dark" in text
        assert "yonguyungcs-pixel/slopcheck" in text


def test_skill_links_point_at_one_file():
    target = (ROOT / "skills" / "slopcheck" / "SKILL.md").resolve()
    text = target.read_text(encoding="utf-8")
    assert "name: slopcheck" in text
    for relative in (
        ".claude/skills/slopcheck/SKILL.md",
        ".cursor/skills/slopcheck/SKILL.md",
        ".agents/skills/slopcheck/SKILL.md",
    ):
        link = ROOT / relative
        assert link.is_symlink()
        assert link.resolve() == target
    hook = ROOT / "examples" / "hooks" / "slopcheck.sh"
    assert os.access(hook, os.X_OK)
