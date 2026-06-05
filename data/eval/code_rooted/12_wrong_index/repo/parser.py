def first_field(line):
    # Bug: returns index 1 (the second field) instead of index 0 (the first).
    # The log shows the wrong field; the off-by-one index is only visible here.
    return line.split(",")[1]
