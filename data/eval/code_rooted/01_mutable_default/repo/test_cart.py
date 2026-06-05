from cart import add_item


def test_each_cart_is_independent():
    assert add_item("apple") == ["apple"]
    # A fresh call should start empty — but the mutable default keeps the old item.
    assert add_item("banana") == ["banana"]
