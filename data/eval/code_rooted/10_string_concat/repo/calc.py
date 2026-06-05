def add(a, b):
    # Bug: concatenates as strings instead of adding numerically.
    # The log shows a string result; the str() coercion is only visible here.
    return str(a) + str(b)
