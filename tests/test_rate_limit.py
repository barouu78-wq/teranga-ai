from collections import deque

from services.rate_limit import allowed_request


class FakeLogger:
    def __init__(self):
        self.messages = []

    def exception(self, message):
        self.messages.append(message)


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.expirations = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds


def test_memory_rate_limit_keeps_window():
    log = deque()
    logger = FakeLogger()

    assert allowed_request(None, logger, "127.0.0.1", log, 2, 60) is True
    assert allowed_request(None, logger, "127.0.0.1", log, 2, 60) is True
    assert allowed_request(None, logger, "127.0.0.1", log, 2, 60) is False


def test_redis_rate_limit_uses_shared_counter():
    redis = FakeRedis()
    logger = FakeLogger()
    log = deque()

    assert allowed_request(redis, logger, "127.0.0.1", log, 2, 60, "chat") is True
    assert allowed_request(redis, logger, "127.0.0.1", log, 2, 60, "chat") is True
    assert allowed_request(redis, logger, "127.0.0.1", log, 2, 60, "chat") is False

    assert len(redis.counts) == 1
    assert list(redis.expirations.values()) == [60]
    assert not log


def test_redis_failure_falls_back_to_memory():
    class BrokenRedis:
        def incr(self, key):
            raise RuntimeError("redis unavailable")

    redis = BrokenRedis()
    logger = FakeLogger()
    log = deque()

    assert allowed_request(redis, logger, "127.0.0.1", log, 1, 60) is True
    assert allowed_request(redis, logger, "127.0.0.1", log, 1, 60) is False
    assert logger.messages == ["Redis rate-limit, fallback mémoire"]
