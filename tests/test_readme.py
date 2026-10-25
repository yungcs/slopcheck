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
