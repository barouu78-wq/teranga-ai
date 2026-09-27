"""Security primitives shared by Teranga AI routes.

The Flask application remains responsible for cookies, headers, and request
validation; this module only handles signed CSRF token values.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time


def sign_token(secret_key: str, value: str) -> str:
    digest = hmac.new(
        secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{value}.{digest}"


def valid_token(token: str, secret_key: str, ttl: int) -> bool:
    if not token or "." not in token:
        return False
    value, _, provided = token.rpartition(".")
    expected = hmac.new(
        secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided, expected):
        return False
    try:
        issued_at = int(value.split(".", 1)[0])
    except (ValueError, IndexError):
        return False
    return 0 <= time.time() - issued_at <= ttl


def issue_csrf(secret_key: str, ttl: int) -> str:
    del ttl  # The expiry is encoded in the validator, not the token payload.
    return sign_token(
        secret_key,
        f"{int(time.time())}.{secrets.token_urlsafe(24)}",
    )
