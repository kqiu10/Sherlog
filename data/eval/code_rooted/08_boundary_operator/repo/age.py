def is_adult(age):
    # Bug: uses > instead of >=, so exactly 18 is wrongly rejected.
    # The log only shows "assert False is True"; the boundary is only visible here.
    return age > 18
