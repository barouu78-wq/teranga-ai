"""Client identity helpers for Teranga AI HTTP requests.

The application supplies the incoming cookie value; this module only handles
format validation and stable hashing of the client identity.
"""

from __future__ import annotations

import hashlib
import re
import secrets

IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9_-]{24,80}")


def client_identity(cookie_value: object) -> str:
    raw = str(cookie_value or "")
    if raw and IDENTITY_PATTERN.fullmatch(raw):
        return raw
    return secrets.token_urlsafe(24)


def abuse_key(ip: object, identity: object) -> str:
    value = f"{str(ip)[:64]}:{str(identity)[:80]}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
