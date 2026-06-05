"""Tests for the deterministic fix-verification engine.

These actually copy the bundled buggy_calculator repo, apply a patch, and run its
tests in a sandbox — proving the engine reports the real test result and never
touches the original files.
"""

import sys
from pathlib import Path

from sherlog.verify import CodeEdit, apply_and_test

REPO = str(Path(__file__).parent.parent / "examples" / "buggy_calculator")
PYTEST = f"{sys.executable} -m pytest -q"

CORRECT = CodeEdit(file="calculator.py", old="return price - pct", new="return price * (1 - pct)")


def test_correct_fix_makes_tests_pass():
    result = apply_and_test(REPO, CORRECT, PYTEST)
    assert result.applied
    assert result.passed
    assert "exit_code=0" in result.output


def test_wrong_fix_still_fails():
    bad = CodeEdit(file="calculator.py", old="return price - pct", new="return price")
    result = apply_and_test(REPO, bad, PYTEST)
    assert result.applied
    assert not result.passed


def test_unmatched_patch_is_not_applied():
    nonmatch = CodeEdit(file="calculator.py", old="this snippet does not exist", new="x")
    result = apply_and_test(REPO, nonmatch, PYTEST)
    assert not result.applied
    assert not result.passed
    assert "match" in result.output


def test_missing_file_reported():
    result = apply_and_test(REPO, CodeEdit(file="nope.py", old="a", new="b"), PYTEST)
    assert not result.applied
    assert "not found" in result.output


def test_original_repo_is_never_mutated():
    before = (Path(REPO) / "calculator.py").read_text()
    apply_and_test(REPO, CORRECT, PYTEST)
    after = (Path(REPO) / "calculator.py").read_text()
    assert before == after  # the real file still has the bug; only the copy was changed
