"""File discovery, excludes, and gitignore."""

import subprocess

from slopcheck.engine import scan
from tests.conftest import rule_ids


def test_exclude_is_opt_in(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.slopcheck]\nexclude = ["demo/**"]\n',
        encoding="utf-8",
    )
    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "bad.py").write_text(
        "def f():\n    try:\n        return 1\n    except:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "good.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
    quiet = scan([tmp_path])
    assert quiet.files_scanned == 1
    assert quiet.findings == []
    loud = scan([demo])
    assert loud.files_scanned == 1
    assert "SLP001" in rule_ids(loud)


def test_gitignore(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".gitignore").write_text("secret.py\n", encoding="utf-8")
    (tmp_path / "secret.py").write_text(
        "def f():\n    try:\n        return 1\n    except:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    report = scan([tmp_path])
    assert report.files_scanned == 1
    assert report.findings == []


def test_explicit_ignored_file_still_scans(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".gitignore").write_text("secret.py\n", encoding="utf-8")
    secret = tmp_path / "secret.py"
    secret.write_text(
        "def f():\n    try:\n        return 1\n    except:\n        pass\n",
        encoding="utf-8",
    )
    report = scan([secret])
    assert "SLP001" in rule_ids(report)
