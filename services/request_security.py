"""Request-level security validation helpers."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from typing import Callable


def validate_json_post(
    *,
    mimetype: object,
    headers: Mapping[str, str],
    cookies: Mapping[str, str],
    expected_mimetype: str,
    origin_allowed: Callable[[], bool],
    csrf_cookie: str,
    csrf_header: str,
    secret_key: str,
    csrf_ttl: int,
    valid_token: Callable[[str, str, int], bool],
) -> str | None:
    if mimetype != expected_mimetype:
        return "content_type"
    if not origin_allowed():
        return "origin"
    cookie_token = cookies.get(csrf_cookie, "")
    header_token = headers.get(csrf_header, "")
    if not cookie_token or not header_token:
        return "csrf"
    try:
        same = hmac.compare_digest(cookie_token, header_token)
    except Exception:
        same = False
    if not same or not valid_token(cookie_token, secret_key, csrf_ttl):
        return "csrf"
    return None
