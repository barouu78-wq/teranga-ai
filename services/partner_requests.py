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

    @staticmethod
    def _expired(item: dict, now: _dt.datetime) -> bool:
        """Vrai si la demande a plus d'un an : la durée annoncée dans la politique de confidentialité."""
        try:
            created = _dt.datetime.strptime(str(item.get("at", "")), "%Y-%m-%d %H:%M UTC").replace(tzinfo=_dt.timezone.utc)
        except ValueError:
            return False
        return (now - created).total_seconds() > _KEEP_SECONDS

    def add(self, entry: dict, now: _dt.datetime | None = None) -> None:
        now = now or _dt.datetime.now(_dt.timezone.utc)
        item = {**entry, "at": now.strftime("%Y-%m-%d %H:%M UTC")}
        raw = json.dumps(item, ensure_ascii=False)
        if self.redis is not None:
            try:
                pipe = self.redis.pipeline(transaction=False)
                pipe.lpush(_KEY, raw)
                pipe.ltrim(_KEY, 0, _KEEP - 1)
                pipe.expire(_KEY, _KEEP_SECONDS)
                pipe.execute()
                # L'expiration de la liste se repousse à chaque ajout : on retire donc aussi les demandes trop anciennes.
                for _ in range(_KEEP):
                    tail = self.redis.lrange(_KEY, -1, -1) or []
                    try:
                        oldest = json.loads(tail[0]) if tail else None
                    except (TypeError, ValueError):
                        oldest = None
                    if not oldest or not self._expired(oldest, now):
                        break
                    self.redis.rpop(_KEY)
                return
            except Exception:
                if self.logger is not None:
                    self.logger.warning("partner-requests redis indisponible, demande gardée en mémoire")
        with self._lock:
            self._memory.appendleft(item)
            while self._memory and self._expired(self._memory[-1], now):
                self._memory.pop()

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
        now = _dt.datetime.now(_dt.timezone.utc)
        items = [item for item in items if not self._expired(item, now)]
        items.sort(key=lambda item: str(item.get("at", "")), reverse=True)
        return items[:limit]
