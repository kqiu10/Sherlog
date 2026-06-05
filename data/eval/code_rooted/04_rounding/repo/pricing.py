def round_price(amount):
    # Bug: int() truncates toward zero instead of rounding, so 2.345 -> 2.34.
    # The log shows the off-by-a-cent symptom; the cause is this truncation.
    return int(amount * 100) / 100
