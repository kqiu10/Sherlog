from stats import average


def test_average_is_not_truncated():
    # The average of 1 and 2 is 1.5, not 1.
    assert average([1, 2]) == 1.5
