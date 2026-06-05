def top_scores(scores):
    # Bug: sorts the caller's list in place, mutating the input as a side effect.
    # The log shows the caller's list was reordered; the cause is this in-place sort.
    scores.sort(reverse=True)
    return scores[:3]
