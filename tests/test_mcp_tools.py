"""Unit tests for the MCP tool functions (the plain `_*` logic, no MCP transport).

These run with no API key/network: they point SHERLOG_TARGET_DIR at the bundled
buggy example repo and check the tools read/search/run as expected, plus that path
traversal is rejected.
"""

from pathlib import Path

import pytest

from sherlog.mcp_server import _read_file, _run_command, _search_code

EXAMPLE_REPO = Path(__file__).parent.parent / "examples" / "buggy_calculator"


@pytest.fixture(autouse=True)
def _point_at_example(monkeypatch):
    monkeypatch.setenv("SHERLOG_TARGET_DIR", str(EXAMPLE_REPO))


def test_read_file_returns_source():
    content = _read_file("calculator.py")
    assert "def apply_discount" in content


def test_read_file_missing():
    assert "not found" in _read_file("does_not_exist.py")


def test_search_code_finds_symbol():
    out = _search_code("apply_discount")
    assert "calculator.py" in out


def test_search_code_no_match():
    assert _search_code("zzz_no_such_symbol_zzz") == "(no matches)"


def test_run_command_captures_output():
    out = _run_command("echo sherlog-ok")
    assert "exit_code=0" in out
    assert "sherlog-ok" in out


def test_path_escape_is_blocked():
    with pytest.raises(ValueError, match="escapes"):
        _read_file("../../../etc/passwd")
