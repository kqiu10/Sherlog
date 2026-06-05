from inventory import get_stock


def test_zero_stock_is_reported_as_zero():
    # An item that exists with 0 units should report 0, not "out of stock".
    assert get_stock({"apples": 0}, "apples") == 0
