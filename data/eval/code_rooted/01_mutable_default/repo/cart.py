def add_item(item, items=[]):
    # Bug lives here — not in the log. The log only shows the symptom (state leaking
    # between calls); you have to read this to see the mutable default argument.
    items.append(item)
    return items
