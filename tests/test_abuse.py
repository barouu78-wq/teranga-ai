from collections import defaultdict, deque
from threading import Lock

from services.abuse import abuse_blocked, record_abuse


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def incrbyfloat(self, key, amount):
        self.values[key] = float(self.values.get(key, 0)) + amount
        return self.values[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds

    def setex(self, key, seconds, value):
        self.values[key] = value
        self.expirations[key] = seconds

    def exists(self, key):
        return int(key in self.values)


class Logger:
    def exception(self, *_args):
        pass


def test_memory_abuse_score_blocks_at_threshold():
    events = defaultdict(deque)
    blocks = {}
    lock = Lock()

    assert not record_abuse(
        "identity",
        "one",
        3,
        redis_client=None,
        logger=Logger(),
        events_by_key=events,
        blocks_by_key=blocks,
        lock=lock,
        score_window=600,
        block_seconds=600,
        score_threshold=8,
    )
    assert record_abuse(
        "identity",
        "two",
        5,
        redis_client=None,
        logger=Logger(),
        events_by_key=events,
        blocks_by_key=blocks,
        lock=lock,
        score_window=600,
        block_seconds=600,
        score_threshold=8,
    )
    assert abuse_blocked(
        "identity",
        redis_client=None,
        logger=Logger(),
        blocks_by_key=blocks,
        lock=lock,
    )


def test_redis_abuse_score_sets_temporary_block():
    redis = FakeRedis()
    events = defaultdict(deque)
    blocks = {}
    lock = Lock()

    assert record_abuse(
        "identity",
        "rate",
        8,
        redis_client=redis,
        logger=Logger(),
        events_by_key=events,
        blocks_by_key=blocks,
        lock=lock,
        score_window=600,
        block_seconds=600,
        score_threshold=8,
    )
    assert abuse_blocked(
        "identity",
        redis_client=redis,
        logger=Logger(),
        blocks_by_key=blocks,
        lock=lock,
    )
