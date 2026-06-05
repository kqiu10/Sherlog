from sequence import count_to


def test_counts_inclusive():
    assert count_to(3) == [1, 2, 3]
