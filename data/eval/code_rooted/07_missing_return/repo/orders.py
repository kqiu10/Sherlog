def order_total(prices):
    # Bug: computes the sum but never returns it, so the function returns None.
    # The log only shows "None"; the missing return is visible only here.
    sum(prices)
