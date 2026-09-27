from services.identity import abuse_key, client_identity


def test_client_identity_keeps_valid_cookie_value():
    value = "A" * 24
    assert client_identity(value) == value


def test_client_identity_replaces_invalid_cookie_value():
    value = client_identity("not-valid")
    assert len(value) >= 24
    assert value != "not-valid"


def test_abuse_key_is_stable_and_bounded():
    first = abuse_key("127.0.0.1", "A" * 24)
    second = abuse_key("127.0.0.1", "A" * 24)
    assert first == second
    assert len(first) == 32
