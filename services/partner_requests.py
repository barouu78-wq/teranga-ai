"""Demandes de partenariat envoyées par le formulaire de /offres-partenaires.

Avec Redis, les demandes sont partagées entre les workers et gardées environ un
an ; sans Redis, elles restent en mémoire (perdues au redémarrage). Seules les
200 dernières sont conservées.
"""

from __future__ import annotations

import datetime as _dt
import json
import threading
from collections import deque

_KEY = "teranga:partner-requests"
_KEEP = 200
_KEEP_SECONDS = 400 * 24 * 3600

KINDS = {
    "hotel": "Hôtel, maison d'hôtes, campement",
    "restaurant": "Restaurant, bar",
    "guide": "Guide, piroguier, excursions",
    "transport": "Taxi, VTC, location de voiture",
    "agence": "Agence de voyage",
    "autre": "Autre activité",
}


class PartnerRequests:
    def __init__(self, redis_client=None, logger=None):
        self.redis = redis_client
        self.logger = logger
        self._memory: deque = deque(maxlen=_KEEP)
        self._lock = threading.Lock()

    def add(self, entry: dict, now: _dt.datetime | None = None) -> None:
        item = {**entry, "at": (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")}
        raw = json.dumps(item, ensure_ascii=False)
        if self.redis is not None:
            try:
                pipe = self.redis.pipeline(transaction=False)
                pipe.lpush(_KEY, raw)
                pipe.ltrim(_KEY, 0, _KEEP - 1)
                pipe.expire(_KEY, _KEEP_SECONDS)
                pipe.execute()
                return
            except Exception:
                if self.logger is not None:
                    self.logger.warning("partner-requests redis indisponible, demande gardée en mémoire")
        with self._lock:
            self._memory.appendleft(item)

    def recent(self, limit: int = 50) -> list[dict]:
        items: list[dict] = []
        if self.redis is not None:
            try:
                for raw in self.redis.lrange(_KEY, 0, limit - 1) or []:
                    try:
                        items.append(json.loads(raw))
                    except (TypeError, ValueError):
                        continue
            except Exception:
                if self.logger is not None:
                    self.logger.warning("partner-requests redis indisponible en lecture")
        with self._lock:
            items.extend(self._memory)
        items.sort(key=lambda item: str(item.get("at", "")), reverse=True)
        return items[:limit]
