"""Shared in-flight request limits for expensive AI endpoints.

A lease is held until the WSGI response iterable is closed, including streamed
responses. Redis uses sorted sets and Lua so per-IP and global admission is
atomic across workers. When Redis is not configured, a locked process-local
fallback is used; production deployments should configure Redis for a shared cap.
"""
from __future__ import annotations

import hashlib
import threading
import time
import uuid
from collections.abc import Iterable
from typing import Any


_ACQUIRE = """
local now = tonumber(ARGV[1])
local expires = tonumber(ARGV[2])
local member = ARGV[3]
local per_ip_limit = tonumber(ARGV[4])
local global_limit = tonumber(ARGV[5])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= per_ip_limit then return 1 end
if redis.call('ZCARD', KEYS[2]) >= global_limit then return 2 end
redis.call('ZADD', KEYS[1], expires, member)
redis.call('ZADD', KEYS[2], expires, member)
redis.call('EXPIRE', KEYS[1], math.ceil((expires - now) / 1000) + 5)
redis.call('EXPIRE', KEYS[2], math.ceil((expires - now) / 1000) + 5)
return 0
"""
_RELEASE = """
redis.call('ZREM', KEYS[1], ARGV[1])
redis.call('ZREM', KEYS[2], ARGV[1])
return 1
"""


class InFlightLimiter:
    def __init__(self, redis_client: Any = None, *, per_ip: int = 2, global_limit: int = 8,
                 lease_seconds: int = 180, clock=time.time):
        self.redis = redis_client
        self.per_ip = max(1, int(per_ip))
        self.global_limit = max(1, int(global_limit))
        self.lease_seconds = max(30, int(lease_seconds))
        self.clock = clock
        self._lock = threading.Lock()
        self._leases: dict[str, tuple[str, float]] = {}

    def acquire(self, ip: str) -> tuple[str | None, str | None]:
        token = uuid.uuid4().hex
        now_ms = int(self.clock() * 1000)
        expires_ms = now_ms + self.lease_seconds * 1000
        ip_hash = hashlib.sha256(str(ip).encode("utf-8")).hexdigest()[:32]
        ip_key = f"teranga:inflight:ip:{ip_hash}"
        global_key = "teranga:inflight:global"
        if self.redis is not None:
            try:
                code = int(self.redis.eval(_ACQUIRE, 2, ip_key, global_key, now_ms,
                                           expires_ms, token, self.per_ip, self.global_limit))
            except Exception:
                # Fail closed: a Redis outage must not silently remove the production cap.
                return None, "unavailable"
            return (token, None) if code == 0 else (None, "ip" if code == 1 else "global")
        with self._lock:
            now = self.clock()
            self._leases = {key: value for key, value in self._leases.items() if value[1] > now}
            ip_count = sum(1 for value in self._leases.values() if value[0] == ip_hash)
            if ip_count >= self.per_ip:
                return None, "ip"
            if len(self._leases) >= self.global_limit:
                return None, "global"
            self._leases[token] = (ip_hash, now + self.lease_seconds)
        return token, None

    def release(self, token: str, ip: str) -> None:
        ip_hash = hashlib.sha256(str(ip).encode("utf-8")).hexdigest()[:32]
        if self.redis is not None:
            try:
                self.redis.eval(_RELEASE, 2, f"teranga:inflight:ip:{ip_hash}",
                                "teranga:inflight:global", token)
            except Exception:
                # Lease expires automatically; don't mask response close errors.
                pass
            return
        with self._lock:
            self._leases.pop(token, None)


class InFlightLimitMiddleware:
    """Limit expensive routes while the full response (including streaming) is active."""
    def __init__(self, app, limiter: InFlightLimiter, *, paths=("/chat", "/api/trip-planner")):
        self.app = app
        self.limiter = limiter
        self.paths = frozenset(paths)

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO") not in self.paths:
            return self.app(environ, start_response)
        ip = environ.get("REMOTE_ADDR", "") or "unknown"
        token, reason = self.limiter.acquire(ip)
        if token is None:
            status = "503 Service Unavailable" if reason in ("global", "unavailable") else "429 Too Many Requests"
            message = ("Service temporairement saturé. Réessaie dans un instant." if status.startswith("503")
                       else "Tu as déjà plusieurs demandes en cours. Attends leur fin avant de réessayer.")
            body = (message + "\n").encode("utf-8")
            start_response(status, [("Content-Type", "text/plain; charset=utf-8"),
                                    ("Content-Length", str(len(body))),
                                    ("Retry-After", "10"), ("Cache-Control", "no-store")])
            return [body]
        released = False
        release_lock = threading.Lock()

        def release():
            nonlocal released
            with release_lock:
                if not released:
                    released = True
                    self.limiter.release(token, ip)

        try:
            iterable = self.app(environ, start_response)
        except BaseException:
            release()
            raise

        class LeaseIterable:
            def __iter__(self):
                try:
                    yield from iterable
                finally:
                    release()

            def close(self):
                try:
                    close = getattr(iterable, "close", None)
                    if callable(close):
                        close()
                finally:
                    release()

        return LeaseIterable()
