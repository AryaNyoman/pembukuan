from app.security import is_allowed_user, parse_allowed_user_ids


def test_allowlist_is_exact_integer_set():
    assert parse_allowed_user_ids("1105904688, 6373275001") == {1105904688, 6373275001}
    assert is_allowed_user(1105904688, {1105904688}) is True
    assert is_allowed_user(999, {1105904688}) is False


def test_invalid_allowlist_values_are_rejected():
    try:
        parse_allowed_user_ids("1105904688,not-an-id")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid user ID to fail")
