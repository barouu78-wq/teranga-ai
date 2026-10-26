from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from services.ai_spend import (
    BudgetExceeded, BudgetUnavailable, DailyAIBudget, _RESERVE_LUA, _SETTLE_LUA,
)


class AtomicFakeRedis:
    """Simule les deux scripts Lua sous un verrou, comme une commande Redis atomique."""
    def __init__(self):
        self.lock = threading.Lock()
        self.hashes = {}

    def eval(self, script, numkeys, key, *args):
        with self.lock:
            data = self.hashes.setdefault(key, {})
            if script == _RESERVE_LUA:
                amount, limit, token = map(int_or_str, args)
                if int(data.get("used", 0)) + int(data.get("reserved", 0)) + amount > limit:
                    return 0
                data["reserved"] = int(data.get("reserved", 0)) + amount
                data["r:" + token] = amount
                return 1
            if script == _SETTLE_LUA:
                token, charged = args
                old = int(data.pop("r:" + str(token), 0))
                if not old:
                    return 0
                data["reserved"] = int(data.get("reserved", 0)) - old
                data["used"] = int(data.get("used", 0)) + int(charged)
                return old
            raise AssertionError("Unexpected Redis script")

    def hgetall(self, key):
        with self.lock:
            return dict(self.hashes.get(key, {}))


def int_or_str(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def test_redis_reservation_is_atomic_under_concurrency():
    redis = AtomicFakeRedis()
    budget = DailyAIBudget(redis, limit_micro_eur=300_000)
    def attempt(_):
        try:
            return budget.reserve("openai", "gpt-5.6-luna", "x" * 20, 3000)
        except BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=40) as pool:
        reservations = list(pool.map(attempt, range(80)))
    admitted = [r for r in reservations if r is not None]
    snapshot = budget.snapshot()
    assert admitted
    assert snapshot["reserved"] <= 1_000_000
    assert len(admitted) < 80
    for reservation in admitted:
        budget.settle(reservation, None)
    assert budget.snapshot()["reserved"] == 0
    assert budget.snapshot()["used"] <= 1_000_000


def test_budget_combines_both_providers_in_same_redis_key():
    redis = AtomicFakeRedis()
    budget = DailyAIBudget(redis, limit_micro_eur=1_000_000)
    openai = budget.reserve("openai", "gpt-5.6-luna", "small", 100)
    anthropic = budget.reserve("anthropic", "claude-opus-5", "small", 100)
    assert openai.key == anthropic.key
    assert budget.snapshot()["reserved"] == openai.amount + anthropic.amount


def test_redis_failure_fails_closed():
    class BrokenRedis:
        def eval(self, *_args):
            raise OSError("redis down")
    budget = DailyAIBudget(BrokenRedis(), require_redis=True)
    with pytest.raises(BudgetUnavailable):
        budget.reserve("openai", "gpt-5.6-luna", "hello", 100)


def test_missing_redis_fails_closed_when_required():
    budget = DailyAIBudget(None, require_redis=True)
    with pytest.raises(BudgetUnavailable):
        budget.reserve("openai", "gpt-5.6-luna", "hello", 100)


def test_limit_blocks_reservation_that_would_cross_cap():
    budget = DailyAIBudget(limit_micro_eur=100)
    with pytest.raises(BudgetExceeded):
        budget.reserve("openai", "unknown-model", "a" * 100, 1000)


def test_unknown_usage_keeps_full_reservation_as_spend():
    budget = DailyAIBudget(limit_micro_eur=1_000_000)
    reservation = budget.reserve("openai", "gpt-5.6-luna", "hello", 100)
    budget.settle(reservation, None)
    snapshot = budget.snapshot()
    assert snapshot["reserved"] == 0
    assert snapshot["used"] == reservation.amount
