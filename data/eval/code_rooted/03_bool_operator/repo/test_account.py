from account import can_withdraw


def test_cannot_overdraw():
    # Withdrawing more than the balance must be rejected.
    assert can_withdraw(balance=50, amount=100) is False
