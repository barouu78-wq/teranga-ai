"""Shared rate-limiting primitives.

The Flask application owns configuration and logging; this module owns the
actual Redis/memory window-counter mechanics so routes do not need to know
how rate limiting is persisted.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import MutableSequence
from threading import Lock
from typing import Any


def allowed_request(
    redis_client: Any,
    logger: Any,
    ip: str,
    log: MutableSequence,
    limit: int,
    window: float,
    bucket: str = "chat",
    lock: Lock | None = None,
) -> bool:
    """Return whether a request fits inside the configured rate window.

    Redis remains the shared source of truth when configured. The caller
    supplies the existing in-process deque and lock for the memory fallback,
    preserving the application's current single-process behavior.
    """
    if redis_client is not None:
        try:
            key = (
                f"teranga:rl:{bucket}:"
                f"{hashlib.sha256(str(ip).encode('utf-8')).hexdigest()[:40]}"
            )
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, int(window))
            return count <= limit
        except Exception:
            logger.exception("Redis rate-limit, fallback mémoire")

    now = time.time()

    def _allow() -> bool:
        while log and now - log[0] > window:
            log.popleft()
        if len(log) >= limit:
            return False
        log.append(now)
        return True

    if lock is None:
        return _allow()
    with lock:
        return _allow()
