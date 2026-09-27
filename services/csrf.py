"""CSRF request-token helpers for Teranga AI."""

from __future__ import annotations

import hmac
from typing import Callable


def valid_request_token(
    cookie_token: object,
    header_token: object,
    *,
    secret_key: str,
    ttl: int,
    validator: Callable[[str, str, int], bool],
) -> bool:
    cookie = str(cookie_token or "")
    header = str(header_token or "")
    if not cookie or not header:
        return False
    try:
        same = hmac.compare_digest(cookie, header)
    except Exception:
        return False
    return same and validator(cookie, secret_key, ttl)
