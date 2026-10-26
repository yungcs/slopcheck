"""CLI routing and exit codes."""

import json
from pathlib import Path

from typer.testing import CliRunner

from slopcheck.cli import app, prepare_argv
from slopcheck.version import __version__
from tests.conftest import ROOT

runner = CliRunner()


def test_prepare_argv():
    assert prepare_argv([]) == ["scan"]
    assert prepare_argv(["."]) == ["scan", "."]
    assert prepare_argv(["--format", "json", "src"]) == ["scan", "--format", "json", "src"]
    assert prepare_argv(["--version"]) == ["--version"]
    assert prepare_argv(["rules", "--help"]) == ["rules", "--help"]
    assert prepare_argv(["prompt", "."]) == ["prompt", "."]
    assert prepare_argv(["--fix-with-agent", "."]) == ["scan", "--fix-with-agent", "."]


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_repo_scan_is_clean():
    result = runner.invoke(app, ["scan", str(ROOT), "--format", "json"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["findings"] == []
    assert payload["score"] == 100
    assert payload["parse_errors"] == []


def test_demo_command_fails():
    result = runner.invoke(app, ["scan", str(ROOT / "demo"), "--format", "json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["score"] < 90
    assert payload["findings"]


def test_missing_path():
    result = runner.invoke(app, ["scan", "does-not-exist-slopcheck"])
    assert result.exit_code == 2


def test_rules_json():
    result = runner.invoke(app, ["rules", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [item["id"] for item in payload][0] == "SLP001"
    assert len(payload) == 15


def test_fix_with_agent_is_prompt(tmp_path: Path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def parse_payload(raw):\n    try:\n        return raw.strip()\n    except:\n        pass\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scan", str(sample), "--fix-with-agent", "--no-config"])
    assert "Fix the slopcheck findings" in result.stdout
    assert "SLP001" in result.stdout


def test_quiet_text(tmp_path: Path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def parse_payload(raw):\n    try:\n        return raw.strip()\n    except:\n        pass\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scan", str(sample), "--quiet", "--no-config", "--no-color"])
    assert result.exit_code == 1
    assert "SLP001" in result.stdout
    assert "score " in result.stdout


def test_syntax_error_fails(tmp_path: Path):
    sample = tmp_path / "bad.py"
    sample.write_text("def (\n", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(sample), "--no-config", "--format", "json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["parse_errors"]
    assert payload["score"] == 100


def test_summary_counts_are_pluralized(tmp_path: Path):
    sample = tmp_path / "one.py"
    sample.write_text("def main():\n    breakpoint()\n", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(sample), "--no-config"])
    assert "scanned 1 file · 2 lines · 1 finding\n" in result.output
    assert "1 finding · score" in result.output
    assert "1 findings" not in result.output
    assert "1 files" not in result.output


def test_plural():
    from slopcheck.models import plural

    assert plural(0, "finding") == "0 findings"
    assert plural(1, "finding") == "1 finding"
    assert plural(20, "finding") == "20 findings"
