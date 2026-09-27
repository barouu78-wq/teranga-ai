"""Identity-cookie policy independent from Flask request globals."""

from __future__ import annotations

IDENTITY_COOKIE_PATHS = frozenset({
    "/chat",
    "/tts",
    "/stt",
    "/image-proxy",
    "/exchange-rates",
})


def should_set_identity_cookie(path: object, existing_value: object) -> bool:
    return str(path or "") in IDENTITY_COOKIE_PATHS and not str(existing_value or "")
