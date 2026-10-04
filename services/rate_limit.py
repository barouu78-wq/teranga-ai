"""Shared rate-limiting primitives.

The Flask application owns configuration and logging; this module owns the
actual Redis/memory window-counter mechanics so routes do not need to know
how rate limiting is persisted.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict, deque
from collections.abc import MutableSequence
from threading import Lock, RLock
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
            # Re-arm the TTL if a previous request crashed between INCR and
            # EXPIRE: a key without expiry would otherwise block forever.
            ttl = getattr(redis_client, "ttl", None)
            if count == 1 or (callable(ttl) and ttl(key) == -1):
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


class BoundedStore(OrderedDict):
    """LRU mapping that creates missing entries and caps the number of keys.

    In-memory rate-limit and abuse state is keyed by client IP/identity. A
    plain ``defaultdict`` grows forever under a flood of distinct keys; this
    store evicts the least recently used entries instead. Active clients are
    touched on every request and therefore stay resident.
    """

    def __init__(self, factory=deque, max_keys: int = 20_000):
        super().__init__()
        self._factory = factory
        self._max_keys = max(1, int(max_keys))
        self._store_lock = RLock()

    def __getitem__(self, key):
        with self._store_lock:
            if key in self:
                self.move_to_end(key)
                return super().__getitem__(key)
            if self._factory is None:
                raise KeyError(key)
            value = self._factory()
            self[key] = value
            return value

    def __setitem__(self, key, value):
        with self._store_lock:
            super().__setitem__(key, value)
            self.move_to_end(key)
            while len(self) > self._max_keys:
                self.popitem(last=False)

    def get(self, key, default=None):
        with self._store_lock:
            if key in self:
                return super().__getitem__(key)
            return default

    def pop(self, key, *args):
        with self._store_lock:
            return super().pop(key, *args)
