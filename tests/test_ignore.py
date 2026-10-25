"""Inline ignore comments and config disables."""

from slopcheck.config import Config
from slopcheck.engine import scan
from slopcheck.ignore import build_ignore_map, parse_ignore
from tests.conftest import ROOT, rule_ids, scan_source


def test_ignore_forms():
    assert parse_ignore("# slopcheck: ignore") == set()
    assert parse_ignore("# slopcheck: ignore[SLP001]") == {"SLP001"}
    assert parse_ignore("# slopcheck: ignore[SLP001, SLP002]") == {"SLP001", "SLP002"}
    assert parse_ignore("# slopcheck: ignore SLP004") == {"SLP004"}
    assert parse_ignore("# nothing to see") is None


def test_same_line_ignore(tmp_path):
    source = (
        "def parse_payload(raw):\n"
        "    try:\n"
        "        return raw.strip()\n"
        "    except:  # slopcheck: ignore[SLP001]\n"
        "        pass\n"
    )
    assert "SLP001" not in rule_ids(scan_source(tmp_path, source))


def test_previous_line_ignore(tmp_path):
    source = (
        "def next_index(index):\n"
        "    # slopcheck: ignore[SLP004]\n"
        "    # increment index\n"
        "    index += 1\n"
        "    return index\n"
    )
    assert "SLP004" not in rule_ids(scan_source(tmp_path, source))


def test_file_disable(tmp_path):
    source = (
        "# slopcheck: disable=SLP001\n"
        "def parse_payload(raw):\n"
        "    try:\n"
        "        return raw.strip()\n"
        "    except:\n"
        "        pass\n"
        "# slopcheck: enable=SLP001\n"
        "def other(raw):\n"
        "    try:\n"
        "        return raw.strip()\n"
        "    except:\n"
        "        pass\n"
    )
    report = scan_source(tmp_path, source)
    lines = [finding.line for finding in report.findings if finding.rule_id == "SLP001"]
    assert lines == [11]


def test_committed_ignore_fixture():
    report = scan([ROOT / "tests" / "fixtures" / "ignored" / "bare_ok.py"])
    assert "SLP001" not in rule_ids(report)


def test_per_file_ignores(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(
        "def parse_payload(raw):\n    try:\n        return raw.strip()\n    except:\n        pass\n",
        encoding="utf-8",
    )
    config = Config(per_file_ignores={"sample.py": ["SLP001"]})
    report = scan([path], config=config, root=tmp_path)
    assert report.findings == []


def test_disable_all_then_enable_one():
    source = "# slopcheck: disable\n# slopcheck: enable=SLP004\nx = 1\n"
    ignore_map = build_ignore_map(source, {"SLP001", "SLP004"})
    assert ignore_map.ignores(3, "SLP001") is True
    assert ignore_map.ignores(3, "SLP004") is False
    assert ignore_map.ignores(1, "SLP001") is True
