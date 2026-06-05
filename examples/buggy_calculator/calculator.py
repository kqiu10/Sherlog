"""A deliberately buggy module used to demo Sherlog's code-reading + verify tools.

The bug is in the CODE, not the log — so diagnosing it correctly requires reading
this file, which is exactly what the MCP tools let the agent do.
"""


def apply_discount(price: float, pct: float) -> float:
    # BUG: subtracts `pct` as a flat amount instead of applying it as a percentage.
    # Correct behavior: price * (1 - pct).
    return price - pct
