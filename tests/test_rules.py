"""Each built-in rule fires on its fixture and stays quiet on clean code."""

from pathlib import Path

import pytest

from slopcheck.engine import scan
from slopcheck.rules import RULES
from tests.conftest import ROOT, rule_ids, scan_source

SLOPPY = ROOT / "tests" / "fixtures" / "sloppy"


@pytest.mark.parametrize("path", sorted(SLOPPY.glob("SLP*.py")))
def test_fixture_flags_its_rule(path: Path):
    rule_id = path.name.split("_", 1)[0]
    report = scan([path])
    assert rule_id in rule_ids(report)


def test_clean_fixture_is_clean():
    report = scan([ROOT / "tests" / "fixtures" / "clean" / "ok.py"])
    assert report.files_scanned == 1
    assert report.findings == []


def test_rule_ids_are_the_fifteen():
    assert [rule.id for rule in RULES] == [f"SLP{number:03d}" for number in range(1, 16)]
    assert len({rule.id for rule in RULES}) == 15


def test_parameter_none_check_is_kept(tmp_path):
    source = "def f(name):\n    if name is not None:\n        return name\n    return ''\n"
    assert "SLP008" not in rule_ids(scan_source(tmp_path, source))


def test_call_result_none_check_is_kept(tmp_path):
    source = (
        "def f(load):\n"
        "    name = load()\n"
        "    if name is not None:\n"
        "        return name\n"
        "    return ''\n"
    )
    assert "SLP008" not in rule_ids(scan_source(tmp_path, source))


def test_why_comment_is_kept(tmp_path):
    source = (
        "def f(attempts):\n"
        "    # Retry once: the upstream closes idle sockets without warning.\n"
        "    attempts += 1\n"
        "    return attempts\n"
    )
    assert "SLP004" not in rule_ids(scan_source(tmp_path, source))


def test_normal_print_is_kept(tmp_path):
    source = "def main(tasks):\n    print(f'tasks={tasks}')\n    return tasks\n"
    assert "SLP005" not in rule_ids(scan_source(tmp_path, source))


def test_optional_import_is_kept(tmp_path):
    source = (
        "try:\n"
        "    import definitely_not_a_real_module_zz\n"
        "except ImportError:\n"
        "    definitely_not_a_real_module_zz = None\n"
    )
    assert "SLP010" not in rule_ids(scan_source(tmp_path, source))


def test_abstract_and_protocol_stubs_are_kept(tmp_path):
    source = (
        "import abc\n"
        "from typing import Protocol\n"
        "\n"
        "class Base(abc.ABC):\n"
        "    @abc.abstractmethod\n"
        "    def fetch(self):\n"
        "        pass\n"
        "\n"
        "class Repo(Protocol):\n"
        "    def get(self, key: str) -> str: ...\n"
    )
    assert "SLP009" not in rule_ids(scan_source(tmp_path, source))


def test_pyi_ellipsis_is_kept(tmp_path):
    source = "def fetch(self) -> str: ...\n"
    report = scan_source(tmp_path, source, name="types.pyi")
    assert "SLP009" not in rule_ids(report)


def test_exit_false_is_kept(tmp_path):
    source = (
        "class CM:\n"
        "    def __exit__(self, exc_type, exc, tb):\n"
        "        try:\n"
        "            return False\n"
        "        except Exception:\n"
        "            return False\n"
    )
    assert "SLP002" not in rule_ids(scan_source(tmp_path, source))


def test_specific_handler_with_logging_is_kept(tmp_path):
    source = (
        "import logging\n"
        "\n"
        "def f(value):\n"
        "    try:\n"
        "        return int(value)\n"
        "    except ValueError:\n"
        "        logging.error('bad value')\n"
        "        raise\n"
    )
    found = rule_ids(scan_source(tmp_path, source))
    assert "SLP001" not in found
    assert "SLP002" not in found
    assert "SLP003" not in found


def test_brand_new_without_sibling_is_kept(tmp_path):
    source = "def brand_new(text):\n    return text.strip()\n"
    assert "SLP013" not in rule_ids(scan_source(tmp_path, source))


def test_new_suffix_with_sibling_is_flagged(tmp_path):
    source = "def save(text):\n    return text\n\ndef save_new(text):\n    return text.strip()\n"
    assert "SLP013" in rule_ids(scan_source(tmp_path, source))


def test_logged_broad_except_is_kept(tmp_path):
    source = (
        "def f(raw):\n"
        "    try:\n"
        "        return raw['id']\n"
        "    except Exception as exc:\n"
        "        sink(exc)\n"
        "        return raw\n"
    )
    assert "SLP002" not in rule_ids(scan_source(tmp_path, source))


def test_relative_import_to_missing_sibling(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (package / "mod.py").write_text("from . import missing_sibling\n", encoding="utf-8")
    from slopcheck.config import Config
    from slopcheck.engine import scan

    report = scan([package / "mod.py"], config=Config(), root=tmp_path)
    assert "SLP010" in rule_ids(report)


def test_relative_import_to_sibling_is_kept(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (package / "sibling.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "mod.py").write_text("from . import sibling\n", encoding="utf-8")
    from slopcheck.config import Config
    from slopcheck.engine import scan

    report = scan([package / "mod.py"], config=Config(), root=tmp_path)
    assert report.findings == []


def test_different_long_functions_are_not_duplicates(tmp_path):
    source = '''
def total_items(items):
    total = 0
    for item in items:
        if item is None:
            continue
        total += int(item)
        total += 1
        total += 2
        if total > 10:
            total -= 1
        if total > 20:
            break
        total += 3
    return total

def label_from(payload):
    name = str(payload.get("name", ""))
    owner = str(payload.get("owner", ""))
    label = name + ":" + owner
    if not label.strip(":"):
        return "empty"
    folded = label.upper()
    if len(folded) > 40:
        folded = folded[:40]
    return folded
'''
    assert "SLP007" not in rule_ids(scan_source(tmp_path, source))
