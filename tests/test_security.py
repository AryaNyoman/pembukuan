from app.security import is_allowed_user, parse_allowed_user_ids


def test_allowlist_is_exact_integer_set():
    assert parse_allowed_user_ids("123456789, 987654321") == {123456789, 987654321}
    assert is_allowed_user(123456789, {123456789}) is True
    assert is_allowed_user(999, {123456789}) is False


def test_invalid_allowlist_values_are_rejected():
    try:
        parse_allowed_user_ids("123456789,not-an-id")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid user ID to fail")
