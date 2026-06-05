from orders import order_total


def test_total():
    assert order_total([10, 20, 5]) == 35
