"""Failing test for the buggy calculator — `run_command` can execute this to
reproduce the failure and (after a fix) verify it's resolved."""

from calculator import apply_discount


def test_apply_discount_ten_percent():
    # 10% off 100 should be 90; the buggy implementation returns 99.9.
    assert apply_discount(100, 0.1) == 90
