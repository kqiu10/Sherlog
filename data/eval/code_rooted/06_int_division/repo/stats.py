def average(numbers):
    # Bug: `//` is integer division, so the average is truncated (1.5 -> 1).
    # The log shows the wrong average; the cause is the floor-division operator.
    return sum(numbers) // len(numbers)
