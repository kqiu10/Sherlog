def last_n(items, n):
    # Bug: off-by-one slice. `-n + 1` drops one extra element, so for n=3 it
    # returns only 2 items. The log shows the wrong list; the cause is this slice.
    return items[-n + 1:]
