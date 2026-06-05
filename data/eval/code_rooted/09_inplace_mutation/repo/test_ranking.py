from ranking import top_scores


def test_does_not_mutate_input():
    data = [3, 1, 2]
    top_scores(data)
    # The caller's list must keep its original order.
    assert data == [3, 1, 2]
