import time

from services.security import issue_csrf, sign_token, valid_token


SECRET = "test-secret"


def test_signed_token_round_trips():
    token = sign_token(SECRET, f"{int(time.time())}.payload")
    assert valid_token(token, SECRET, 3600) is True


def test_signed_token_rejects_tampering():
    token = sign_token(SECRET, "12345.payload")
    value, _, _ = token.rpartition(".")
    assert valid_token(f"{value}.bad", SECRET, 3600) is False


def test_csrf_token_expires():
    token = sign_token(SECRET, f"{int(time.time()) - 20}.payload")
    assert valid_token(token, SECRET, 10) is False


def test_issue_csrf_returns_valid_token():
    token = issue_csrf(SECRET, 3600)
    assert valid_token(token, SECRET, 3600) is True
