def get_stock(inventory, item):
    # Bug: `or` treats a real 0 quantity as "missing" and returns the default.
    # The log shows the wrong value, but the cause is only visible here.
    return inventory.get(item) or "out of stock"
