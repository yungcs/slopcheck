"""pyproject configuration."""

from slopcheck.config import ConfigError, load_config
from slopcheck.engine import exit_code, scan
from tests.conftest import rule_ids


def test_pyproject_table(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.slopcheck]\n"
        'exclude = ["skip/**"]\n'
        'ignore = ["SLP004"]\n'
        "min-score = 80\n"
        "\n"
        "[tool.slopcheck.per-file-ignores]\n"
        '"legacy.py" = ["SLP001"]\n'
        "\n"
        "[tool.slopcheck.rules.SLP011]\n"
        "max_depth = 1\n",
        encoding="utf-8",
    )
    config = load_config(pyproject)
    assert config.exclude == ["skip/**"]
    assert config.ignore == ["SLP004"]
    assert config.min_score == 80
    assert config.per_file_ignores["legacy.py"] == ["SLP001"]
    assert config.rule_options["SLP011"]["max_depth"] == 1


def test_bad_severity(tmp_path):
    path = tmp_path / "slopcheck.toml"
    path.write_text('[tool.slopcheck.severity]\nSLP001 = "fatal"\n', encoding="utf-8")
    try:
        load_config(path)
    except ConfigError as exc:
        assert "severity" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_select_limits_rules(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def parse_payload(raw):\n"
        "    try:\n"
        "        return raw.strip()\n"
        "    except:\n"
        "        pass\n"
        "def next_index(index):\n"
        "    # increment index\n"
        "    index += 1\n"
        "    return index\n",
        encoding="utf-8",
    )
    from slopcheck.config import Config

    report = scan([sample], config=Config(select=["SLP004"]), root=tmp_path)
    assert rule_ids(report) == {"SLP004"}


def test_notes_do_not_fail_without_min_score(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def next_index(index):\n    # increment index\n    index += 1\n    return index\n",
        encoding="utf-8",
    )
    from slopcheck.config import Config

    report = scan([sample], config=Config(), root=tmp_path)
    assert rule_ids(report) == {"SLP004"}
    assert exit_code(report, min_score=None) == 0
    assert exit_code(report, min_score=100) == 1
