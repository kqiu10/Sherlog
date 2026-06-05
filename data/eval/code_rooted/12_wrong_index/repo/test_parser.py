from parser import first_field


def test_returns_first_field():
    assert first_field("alice,bob,carol") == "alice"
