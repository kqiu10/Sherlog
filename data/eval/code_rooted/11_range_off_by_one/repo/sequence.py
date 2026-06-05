def count_to(n):
    # Bug: range(1, n) stops at n-1; it should be range(1, n + 1) to include n.
    # The log shows a list missing its last element; the cause is this range bound.
    return list(range(1, n))
