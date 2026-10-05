"""Cache des réponses aux questions fréquentes.

Une même première question (« Que visiter à Dakar ? ») posée par plusieurs
visiteurs reçoit la réponse déjà générée : réponse instantanée et aucun appel
OpenAI. Seules les questions sans contexte personnel ni donnée changeante sont
mises en cache : pas d'historique, pas de recherche web, pas de météo en direct,
pas de planificateur, pas de lieu ou de voyage sélectionné.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from typing import Any

CACHE_VERSION = "v1"
DEFAULT_TTL = 12 * 3600
MAX_MESSAGE_CHARS = 240
MIN_REPLY_CHARS = 60
_MEMORY_MAX = 500
_PREFIX = "teranga:answer:"


def _normalize_message(message: str) -> str:
    text = unicodedata.normalize("NFKC", str(message or "")).lower().strip()
    text = text.replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"[\s?!.…]+$", "", text)


def cache_key(payload: dict[str, Any], raw: dict[str, Any] | None, *, model: str) -> str | None:
    """Clé de cache, ou None si la demande ne doit pas être mise en cache."""
    raw = raw if isinstance(raw, dict) else {}
    if raw.get("history"):
        return None
    if any(str(raw.get(name) or "").strip() for name in ("context_place", "trip_context", "trip_edit_request")):
        return None
    if raw.get("action_confirmed") or raw.get("action_request_id"):
        return None
    if (
        payload.get("use_web")
        or payload.get("planner")
        or payload.get("deep_reasoning")
        or payload.get("live_weather")
        or payload.get("photo_only")
        or payload.get("trip_edit_proposal")
        or (payload.get("action_request") or {}).get("enabled")
    ):
        return None
    message = _normalize_message(payload.get("message", ""))
    if not message or len(message) > MAX_MESSAGE_CHARS:
        return None
    parts = (
        CACHE_VERSION,
        str(model or ""),
        str(payload.get("language") or "fr"),
        str(payload.get("audience") or ""),
        ",".join(payload.get("modes") or ()),
        message,
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


class AnswerCache:
    """Redis si disponible (partagé entre workers), sinon mémoire locale bornée."""

    def __init__(self, redis_client=None, *, ttl: int = DEFAULT_TTL, enabled: bool = True, logger=None):
        self._redis = redis_client
        self._ttl = max(60, int(ttl))
        self.enabled = enabled
        self._logger = logger
        self._memory: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls, redis_client=None, logger=None) -> "AnswerCache":
        enabled = os.getenv("ANSWER_CACHE", "1").strip().lower() not in {"0", "false", "no", "off"}
        try:
            ttl = int(os.getenv("ANSWER_CACHE_TTL", str(DEFAULT_TTL)))
        except ValueError:
            ttl = DEFAULT_TTL
        return cls(redis_client, ttl=ttl, enabled=enabled, logger=logger)

    def get(self, key: str | None) -> dict[str, Any] | None:
        if not key or not self.enabled:
            return None
        raw = None
        if self._redis is not None:
            try:
                raw = self._redis.get(_PREFIX + key)
            except Exception:
                if self._logger is not None:
                    self._logger.warning("answer_cache_redis_get_failed")
        if raw is None:
            with self._lock:
                entry = self._memory.get(key)
                if entry and entry[0] > time.time():
                    self._memory.move_to_end(key)
                    raw = entry[1]
                elif entry:
                    self._memory.pop(key, None)
        if not raw:
            return None
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) and value.get("reply") else None

    def set(self, key: str | None, *, reply: str, sources=None, image=None, maps=None) -> bool:
        reply = str(reply or "").strip()
        if not key or not self.enabled or len(reply) < MIN_REPLY_CHARS:
            return False
        raw = json.dumps({"reply": reply, "sources": sources or [], "image": image, "map": maps}, ensure_ascii=False)
        if self._redis is not None:
            try:
                self._redis.setex(_PREFIX + key, self._ttl, raw)
            except Exception:
                if self._logger is not None:
                    self._logger.warning("answer_cache_redis_set_failed")
        with self._lock:
            self._memory[key] = (time.time() + self._ttl, raw)
            self._memory.move_to_end(key)
            while len(self._memory) > _MEMORY_MAX:
                self._memory.popitem(last=False)
        return True


def replay_chunks(text: str, size: int = 48):
    """Découpe une réponse en morceaux sur des espaces, pour un affichage progressif."""
    text = str(text or "")
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            space = text.rfind(" ", start + 1, end)
            if space > start:
                end = space + 1
        yield text[start:end]
        start = end
