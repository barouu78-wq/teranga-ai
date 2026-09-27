"""Abuse scoring and temporary blocking primitives.

The application supplies storage, logging and synchronization dependencies so
this module stays independent from Flask globals.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import MutableMapping, MutableSequence
from threading import Lock
from typing import Any


def redis_key(prefix: str, value: object) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:40]
    return f"teranga:abuse:{prefix}:{digest}"


def record_abuse(
    identity: object,
    kind: str,
    weight: int = 1,
    *,
    redis_client: Any,
    logger: Any,
    events_by_key: MutableMapping[str, MutableSequence[tuple[float, str, int]]],
    blocks_by_key: MutableMapping[str, float],
    lock: Lock,
    score_window: float,
    block_seconds: float,
    score_threshold: int,
) -> bool:
    now = time.time()
    key = str(identity)[:64]
    safe_weight = min(int(weight), 5)

    if redis_client is not None:
        try:
            key_name = redis_key("score", key)
            score = redis_client.incrbyfloat(key_name, safe_weight)
            redis_client.expire(key_name, int(score_window))
            if score >= score_threshold:
                redis_client.setex(redis_key("block", key), int(block_seconds), "1")
                return True
            return False
        except Exception:
            logger.exception("Redis abuse-score, fallback mémoire")

    with lock:
        events = events_by_key[key]
        while events and now - events[0][0] > score_window:
            events.popleft()
        events.append((now, kind, safe_weight))
        score = sum(item[2] for item in events)
        if score >= score_threshold:
            blocks_by_key[key] = now + block_seconds
            return True
    return False


def abuse_blocked(
    identity: object,
    *,
    redis_client: Any,
    logger: Any,
    blocks_by_key: MutableMapping[str, float],
    lock: Lock,
) -> bool:
    now = time.time()
    key = str(identity)[:64]

    if redis_client is not None:
        try:
            return bool(redis_client.exists(redis_key("block", key)))
        except Exception:
            logger.exception("Redis abuse-block, fallback mémoire")

    with lock:
        until = blocks_by_key.get(key, 0)
        if until > now:
            return True
        if until:
            blocks_by_key.pop(key, None)
    return False

# Kept as a standalone module so abuse behavior can be tested independently.
