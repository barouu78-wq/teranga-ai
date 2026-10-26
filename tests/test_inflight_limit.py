from services.inflight_limit import InFlightLimiter, InFlightLimitMiddleware


def test_memory_limiter_caps_per_ip_and_releases():
    limiter = InFlightLimiter(per_ip=1, global_limit=2)
    token, reason = limiter.acquire("203.0.113.1")
    assert token and reason is None
    assert limiter.acquire("203.0.113.1") == (None, "ip")
    other, reason = limiter.acquire("203.0.113.2")
    assert other and reason is None
    limiter.release(token, "203.0.113.1")
    token2, reason = limiter.acquire("203.0.113.1")
    assert token2 and reason is None


def test_memory_limiter_caps_global_requests():
    limiter = InFlightLimiter(per_ip=2, global_limit=1)
    token, _ = limiter.acquire("203.0.113.1")
    assert token
    assert limiter.acquire("203.0.113.2") == (None, "global")


def test_redis_failure_fails_closed():
    class BrokenRedis:
        def eval(self, *_args):
            raise RuntimeError("redis unavailable")

    limiter = InFlightLimiter(BrokenRedis())
    assert limiter.acquire("203.0.113.1") == (None, "unavailable")


def test_middleware_releases_lease_when_stream_closes():
    limiter = InFlightLimiter(per_ip=1, global_limit=1)
    closed = []

    class Stream:
        def __iter__(self):
            yield b"part"

        def close(self):
            closed.append(True)

    def app(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return Stream()

    middleware = InFlightLimitMiddleware(app, limiter, paths=("/chat",))
    environ = {"PATH_INFO": "/chat", "REMOTE_ADDR": "203.0.113.5"}
    statuses = []
    response = middleware(environ, lambda status, _headers: statuses.append(status))
    assert next(iter(response)) == b"part"
    assert limiter.acquire("203.0.113.5")[1] == "ip"
    response.close()
    assert closed == [True]
    token, reason = limiter.acquire("203.0.113.5")
    assert token and reason is None


def test_middleware_returns_429_for_per_ip_limit():
    limiter = InFlightLimiter(per_ip=1, global_limit=2)
    token, _ = limiter.acquire("203.0.113.9")
    assert token
    statuses = []
    middleware = InFlightLimitMiddleware(lambda *_: [], limiter, paths=("/chat",))
    body = b"".join(middleware({"PATH_INFO": "/chat", "REMOTE_ADDR": "203.0.113.9"},
                               lambda status, _headers: statuses.append(status)))
    assert statuses == ["429 Too Many Requests"]
    assert b"plusieurs demandes en cours" in body
