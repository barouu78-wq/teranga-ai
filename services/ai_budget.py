"""Plafond global de dépense IA : un nombre de requêtes vers l'IA par jour pour tout le site (audit V3, P1-4).

Les limites par adresse IP ne bornent pas la facture quand beaucoup d'adresses appellent en même temps.
Au-delà du plafond et jusqu'à minuit (heure de Dakar, qui est l'heure UTC) : le chat répond avec la base
vérifiée, la voix et le planificateur répondent 503. Réglage Render : AI_PLAFOND_JOUR (500 par défaut).

On compte les requêtes, pas chaque appel : quand le premier fournisseur échoue, le secours (Claude ou
OpenAI) fait un second appel pour la même requête, non compté. Au pire, 2 appels par requête.

Le compteur vit dans Redis, partagé par tous les processus. Sans Redis, ou si Redis ne répond pas, chaque
processus compte de son côté, en repartant du dernier total partagé qu'il a vu : le plafond réel est alors
au plus « plafond × nombre de processus ».
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone

DEFAULT_DAILY_LIMIT = 500
KEY_PREFIX = "teranga:ia_jour:"
KEY_TTL = 2 * 86400  # la clé du jour disparaît seule


def daily_limit(raw=None) -> int:
    """AI_PLAFOND_JOUR ; une valeur vide, invalide ou ≤ 0 garde le plafond par défaut (jamais « illimité »)."""
    value = os.getenv("AI_PLAFOND_JOUR", "") if raw is None else raw
    try:
        limit = int(str(value).strip())
    except ValueError:
        return DEFAULT_DAILY_LIMIT
    return limit if limit > 0 else DEFAULT_DAILY_LIMIT


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AiBudget:
    def __init__(self, redis_client=None, *, limit=None, logger=None, now=None):
        self.redis = redis_client
        self.limit = daily_limit() if limit is None else limit
        self.logger = logger
        self._now = now or _utc_now
        self._lock = threading.Lock()
        self._memory_day = ""
        self._memory_count = 0
        self._reported_day = ""

    def take(self) -> bool:
        """Compte un appel payant. False : le plafond du jour est atteint, l'appel ne doit pas partir."""
        day = self._now().strftime("%Y-%m-%d")
        count = self._shared_count(day)
        if count is None:
            count = self._local_count(day)
        if count <= self.limit:
            return True
        if self.logger is not None and self._reported_day != day:
            self._reported_day = day  # une seule ligne par jour et par processus
            self.logger.warning("ia_plafond_atteint jour=%s plafond=%s", day, self.limit)
        return False

    def retry_after(self) -> int:
        """Secondes jusqu'à minuit UTC (au moins une minute), pour l'en-tête Retry-After."""
        now = self._now()
        midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        return max(60, int((midnight - now).total_seconds()))

    def reset(self) -> None:
        """Remet à zéro le compteur local (tests)."""
        with self._lock:
            self._memory_day, self._memory_count, self._reported_day = "", 0, ""

    def _shared_count(self, day):
        if self.redis is None:
            return None
        key = KEY_PREFIX + day
        try:
            count = int(self.redis.incr(key))
            if count == 1:
                self.redis.expire(key, KEY_TTL)
            with self._lock:
                # Dernier total partagé vu : si Redis tombe en panne plus tard, le compte local repart de là.
                self._memory_day, self._memory_count = day, count
            return count
        except Exception:  # noqa: BLE001 - Redis en panne : le compteur local prend le relais
            if self.logger is not None:
                self.logger.warning("ia_plafond_redis_indisponible")
            return None

    def _local_count(self, day):
        with self._lock:
            if self._memory_day != day:
                self._memory_day, self._memory_count = day, 0
            self._memory_count += 1
            return self._memory_count
