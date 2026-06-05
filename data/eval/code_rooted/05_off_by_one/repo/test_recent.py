from recent import last_n


def test_returns_last_three():
    # The last 3 of five items should be [3, 4, 5].
    assert last_n([1, 2, 3, 4, 5], 3) == [3, 4, 5]
