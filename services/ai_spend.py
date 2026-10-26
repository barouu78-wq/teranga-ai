"""Plafond quotidien partagé des coûts IA (OpenAI + Anthropic).

Les montants sont conservés en micro-euros. Redis Lua réserve atomiquement un
budget avant chaque appel, puis transforme la réservation en dépense après
lecture de l'usage. Si l'usage est inconnu, la réservation entière est imputée
par prudence. Le plafond se réinitialise à minuit UTC.
"""
from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DAILY_LIMIT_MICRO_EUR = 5_000_000
# Prix par million de tokens, utilisés pour les réservations et le rapprochement.
# OpenAI : https://developers.openai.com/api/docs/pricing
# Les valeurs inconnues utilisent volontairement un tarif haut pour éviter de
# sous-estimer un modèle nouvellement configuré. USD/EUR=1 est conservateur.
OPENAI_RATES = {
    "gpt-5.6-luna": (1, 6),   # prix en micro-euros par token : $0.20 / $1.20 par MTok
    "gpt-5.6-sol": (4, 20),  # $4 / $20 par MTok
}
ANTHROPIC_RATES = {
    # Claude Opus 5.5 : tarifs publiés par Anthropic, 4 $ / 20 $ par MTok.
    # https://www.anthropic.com/claude-opus-5-5
    "claude-opus-5-5": (4, 20),
    "claude-opus-5": (5, 25),
    "claude-opus-4-8": (5, 25),
    "claude-opus-4-7": (5, 25),
    "claude-opus-4-6": (5, 25),
    "claude-sonnet-4-6": (3, 15),
    "claude-haiku-4-5": (1, 5),
}
UNKNOWN_RATES = (60, 300)
_SEARCH_CALL_MICRO_EUR = 10_000  # $0.01/appel, au taux prudent de 1 USD = 1 EUR

_RESERVE_LUA = """
local used = tonumber(redis.call('HGET', KEYS[1], 'used') or '0')
local reserved = tonumber(redis.call('HGET', KEYS[1], 'reserved') or '0')
local amount = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
if used + reserved + amount > limit then return 0 end
redis.call('HINCRBY', KEYS[1], 'reserved', amount)
redis.call('HSET', KEYS[1], 'r:' .. ARGV[3], amount)
redis.call('EXPIRE', KEYS[1], 172800)
return 1
"""
_SETTLE_LUA = """
local amount = tonumber(redis.call('HGET', KEYS[1], 'r:' .. ARGV[1]) or '0')
if amount == 0 then return 0 end
redis.call('HINCRBY', KEYS[1], 'reserved', -amount)
redis.call('HINCRBY', KEYS[1], 'used', tonumber(ARGV[2]))
redis.call('HDEL', KEYS[1], 'r:' .. ARGV[1])
redis.call('EXPIRE', KEYS[1], 172800)
return amount
"""


class BudgetExceeded(RuntimeError):
    """Le budget quotidien est épuisé ou ne peut pas accueillir cette réservation."""


class BudgetUnavailable(RuntimeError):
    """Le compteur Redis est indisponible : l'appel IA doit être refusé."""


@dataclass(frozen=True)
class Reservation:
    token: str
    key: str
    amount: int
    provider: str
    model: str
    search_fee: int = 0


def seconds_until_reset(now: float | None = None) -> int:
    current = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc)
    tomorrow = current.date().toordinal() + 1
    next_day = datetime.fromordinal(tomorrow).replace(tzinfo=timezone.utc)
    return max(1, math.ceil((next_day - current).total_seconds()))


def _utc_key(now: float | None = None) -> str:
    day = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc).date().isoformat()
    return f"teranga:ai-spend:{day}"


def _serialize(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value or "")


def _rates(provider: str, model: str) -> tuple[int, int]:
    name = str(model or "").lower()
    if provider == "openai":
        for key, rates in OPENAI_RATES.items():
            if key in name:
                return rates
    elif provider == "anthropic":
        for key, rates in ANTHROPIC_RATES.items():
            if key in name:
                return rates
    return UNKNOWN_RATES


def estimate_micro_eur(provider: str, model: str, input_data: Any, max_output_tokens: int,
                        *, web_search: bool = False, search_calls: int = 1) -> tuple[int, int]:
    # Borne prudente : compter chaque octet UTF-8 comme un token, puis ajouter
    # 25 % pour les formats et instructions internes ajoutés par le fournisseur.
    input_tokens = math.ceil(len(_serialize(input_data).encode("utf-8")) * 1.25)
    output_tokens = max(1, int(max_output_tokens or 4000))
    in_rate, out_rate = _rates(provider, model)
    token_cost = input_tokens * in_rate + output_tokens * out_rate
    fee = _SEARCH_CALL_MICRO_EUR * max(0, int(search_calls)) if web_search else 0
    reserve = math.ceil(token_cost * 1.25) + fee
    return reserve, fee


def actual_micro_eur(provider: str, model: str, usage: Any, search_fee: int = 0) -> int | None:
    if usage is None:
        return None
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if input_tokens is None and isinstance(usage, dict):
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
    if input_tokens is None or output_tokens is None:
        return None
    in_rate, out_rate = _rates(provider, model)
    return max(0, int(input_tokens)) * in_rate + max(0, int(output_tokens)) * out_rate + search_fee


class DailyAIBudget:
    def __init__(self, redis_client: Any = None, *, limit_micro_eur: int = DAILY_LIMIT_MICRO_EUR,
                 require_redis: bool = False, clock=time.time):
        self.redis = redis_client
        self.limit = max(1, int(limit_micro_eur))
        self.require_redis = bool(require_redis)
        self.clock = clock
        self._lock = threading.Lock()
        self._memory: dict[str, dict[str, int]] = {}

    def reserve(self, provider: str, model: str, input_data: Any, max_output_tokens: int,
                *, web_search: bool = False, search_calls: int = 1) -> Reservation:
        amount, fee = estimate_micro_eur(provider, model, input_data, max_output_tokens,
                                          web_search=web_search, search_calls=search_calls)
        key = _utc_key(self.clock())
        token = uuid.uuid4().hex
        if self.redis is not None:
            try:
                admitted = int(self.redis.eval(_RESERVE_LUA, 1, key, amount, self.limit, token))
            except Exception as exc:
                raise BudgetUnavailable("Compteur de budget IA indisponible") from exc
            if not admitted:
                raise BudgetExceeded("Plafond quotidien IA de 5 EUR atteint")
        elif self.require_redis:
            raise BudgetUnavailable("Redis requis pour protéger le budget IA")
        else:
            with self._lock:
                state = self._memory.setdefault(key, {"used": 0, "reserved": 0})
                if state["used"] + state["reserved"] + amount > self.limit:
                    raise BudgetExceeded("Plafond quotidien IA de 5 EUR atteint")
                state["reserved"] += amount
                state[token] = amount
        return Reservation(token, key, amount, provider, model, fee)

    def reserve_fixed(self, provider: str, model: str, amount_micro_eur: int) -> Reservation:
        """Réserve un coût prudent fixe pour les API audio sans usage tokenisé."""
        amount = max(1, int(amount_micro_eur))
        key = _utc_key(self.clock())
        token = uuid.uuid4().hex
        if self.redis is not None:
            try:
                admitted = int(self.redis.eval(_RESERVE_LUA, 1, key, amount, self.limit, token))
            except Exception as exc:
                raise BudgetUnavailable("Compteur de budget IA indisponible") from exc
            if not admitted:
                raise BudgetExceeded("Plafond quotidien IA de 5 EUR atteint")
        elif self.require_redis:
            raise BudgetUnavailable("Redis requis pour protéger le budget IA")
        else:
            with self._lock:
                state = self._memory.setdefault(key, {"used": 0, "reserved": 0})
                if state["used"] + state["reserved"] + amount > self.limit:
                    raise BudgetExceeded("Plafond quotidien IA de 5 EUR atteint")
                state["reserved"] += amount
                state[token] = amount
        return Reservation(token, key, amount, provider, model)

    def settle(self, reservation: Reservation, usage: Any = None) -> int:
        actual = actual_micro_eur(reservation.provider, reservation.model, usage, reservation.search_fee)
        # Si le fournisseur ne renvoie pas l'usage (timeout/flux interrompu),
        # conserver toute la réservation évite de libérer un coût potentiellement facturé.
        charged = reservation.amount if actual is None else max(0, actual)
        if self.redis is not None:
            try:
                self.redis.eval(_SETTLE_LUA, 1, reservation.key, reservation.token, charged)
            except Exception as exc:
                # La réservation Redis reste en place si le rapprochement échoue.
                raise BudgetUnavailable("Impossible de rapprocher le budget IA") from exc
        elif not self.require_redis:
            with self._lock:
                state = self._memory.setdefault(reservation.key, {"used": 0, "reserved": 0})
                old = state.pop(reservation.token, 0)
                state["reserved"] = max(0, state["reserved"] - old)
                state["used"] += charged
        return charged

    def snapshot(self) -> dict[str, int]:
        key = _utc_key(self.clock())
        if self.redis is not None:
            try:
                values = self.redis.hgetall(key)
                return {"used": int(values.get("used", 0)), "reserved": int(values.get("reserved", 0))}
            except Exception as exc:
                raise BudgetUnavailable("Compteur de budget IA indisponible") from exc
        with self._lock:
            state = self._memory.get(key, {})
            return {"used": int(state.get("used", 0)), "reserved": int(state.get("reserved", 0))}


_guard: DailyAIBudget | None = None
_guard_lock = threading.Lock()


def configure_spend_guard(redis_client: Any = None, *, enabled: bool = True, require_redis: bool = False) -> None:
    global _guard
    with _guard_lock:
        _guard = DailyAIBudget(redis_client, require_redis=require_redis) if enabled else None


def get_spend_guard() -> DailyAIBudget | None:
    return _guard


def _usage_from_response(response: Any) -> Any:
    usage = getattr(response, "usage", None)
    if usage is not None:
        return usage
    nested = getattr(response, "response", None)
    return getattr(nested, "usage", None)


class GuardedStream:
    """Conserve la réservation jusqu'à l'usage final ou ferme prudemment le budget."""
    def __init__(self, stream: Any, budget: DailyAIBudget, reservation: Reservation):
        self.stream, self.budget, self.reservation = stream, budget, reservation
        self.settled = False

    def __iter__(self):
        try:
            for event in self.stream:
                if getattr(event, "type", "") in ("response.completed", "response.incomplete"):
                    response = getattr(event, "response", None)
                    self._settle(_usage_from_response(response))
                yield event
        finally:
            if not self.settled:
                self._settle(None)

    def _settle(self, usage: Any) -> None:
        if not self.settled:
            self.budget.settle(self.reservation, usage)
            self.settled = True

    def close(self):
        try:
            close = getattr(self.stream, "close", None)
            if callable(close):
                close()
        finally:
            if not self.settled:
                self._settle(None)


def create_openai_response(client: Any, kwargs: dict[str, Any]):
    """Réserve avant Responses API, rapproche l'usage et enveloppe les flux."""
    budget = get_spend_guard()
    if budget is None:
        return client.responses.create(**kwargs)
    model = str(kwargs.get("model") or "")
    reservation = budget.reserve(
        "openai", model, kwargs,
        kwargs.get("max_output_tokens", 4000),
        web_search=any("web_search" in str(tool.get("type", "")) for tool in kwargs.get("tools", []) if isinstance(tool, dict)),
        search_calls=1,
    )
    try:
        response = client.responses.create(**kwargs)
    except Exception:
        budget.settle(reservation, None)
        raise
    if kwargs.get("stream"):
        return GuardedStream(response, budget, reservation)
    budget.settle(reservation, _usage_from_response(response))
    return response
