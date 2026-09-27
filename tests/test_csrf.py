from services.csrf import valid_request_token


def test_valid_request_token_requires_matching_valid_tokens():
    calls = []

    def validator(token, secret, ttl):
        calls.append((token, secret, ttl))
        return True

    assert valid_request_token(
        "token", "token", secret_key="secret", ttl=60, validator=validator
    )
    assert calls == [("token", "secret", 60)]


def test_valid_request_token_rejects_missing_or_mismatched_tokens():
    validator = lambda token, secret, ttl: True
    assert not valid_request_token("", "token", secret_key="s", ttl=60, validator=validator)
    assert not valid_request_token("token", "other", secret_key="s", ttl=60, validator=validator)
    assert not valid_request_token("token", "token", secret_key="s", ttl=60, validator=lambda *args: False)
