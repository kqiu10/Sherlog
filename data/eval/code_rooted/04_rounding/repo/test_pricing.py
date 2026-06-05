from pricing import round_price


def test_rounds_half_up():
    # 2.345 should round to 2.35, not truncate to 2.34.
    assert round_price(2.345) == 2.35
