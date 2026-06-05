def can_withdraw(balance, amount):
    # Bug: should require sufficient balance AND a positive amount; uses `or`,
    # so it approves withdrawals larger than the balance. Cause is only in the code.
    return balance >= amount or amount > 0
