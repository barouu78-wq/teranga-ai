"""Compteur des clics vers les partenaires (/go/…), sans donnée personnelle.

Chaque clic ajoute 1 au couple (type de lien, page d'origine) du mois en cours.
Avec Redis, les compteurs sont partagés entre les workers et survivent aux
redéploiements ; sans Redis, ils restent en mémoire (perdus au redémarrage).
"""

from __future__ import annotations

import datetime as _dt
import threading
from collections import Counter

_PREFIX = "teranga:clicks:"
_KEEP_SECONDS = 400 * 24 * 3600  # un peu plus d'un an d'historique


def _month(day: _dt.date | None = None) -> str:
    return (day or _dt.date.today()).strftime("%Y-%m")


def _previous_months(count: int, today: _dt.date | None = None) -> list[str]:
    day = (today or _dt.date.today()).replace(day=1)
    months = []
    for _ in range(count):
        months.append(day.strftime("%Y-%m"))
        day = (day - _dt.timedelta(days=1)).replace(day=1)
    return months


class ClickStats:
    def __init__(self, redis_client=None, logger=None):
        self.redis = redis_client
        self.logger = logger
        self._memory: dict[str, Counter] = {}
        self._lock = threading.Lock()

    def record(self, kind: str, source: str, day: _dt.date | None = None, max_fields: int | None = None) -> None:
        field = f"{kind}|{source or '-'}"
        month = _month(day)
        # Origine libre (nom de partenaire du widget) : au-delà de max_fields lignes dans le mois, une nouvelle
        # origine est comptée « autre », pour qu'un script ne puisse pas remplir Redis de noms inventés.
        if max_fields is not None and not self._has_room(month, field, max_fields):
            field = f"{kind}|autre"
        if self.redis is not None:
            try:
                key = _PREFIX + month
                # Un seul aller-retour Redis (le clic attend avant la redirection).
                pipe = self.redis.pipeline(transaction=False) if hasattr(self.redis, "pipeline") else None
                if pipe is not None:
                    pipe.hincrby(key, field, 1)
                    pipe.expire(key, _KEEP_SECONDS)
                    pipe.execute()
                else:
                    self.redis.hincrby(key, field, 1)
                    self.redis.expire(key, _KEEP_SECONDS)
                return
            except Exception:
                if self.logger is not None:
                    self.logger.warning("click-stats redis indisponible, comptage en mémoire")
        with self._lock:
            self._memory.setdefault(month, Counter())[field] += 1
            for old_month in sorted(self._memory)[:-13]:  # environ un an en mémoire
                self._memory.pop(old_month, None)

    def _has_room(self, month: str, field: str, max_fields: int) -> bool:
        if self.redis is not None:
            try:
                key = _PREFIX + month
                return bool(self.redis.hexists(key, field)) or self.redis.hlen(key) < max_fields
            except Exception:
                pass  # record() retombe alors sur la mémoire et le signale
        with self._lock:
            counts = self._memory.get(month, Counter())
            return field in counts or len(counts) < max_fields

    def month_counts(self, month: str) -> Counter:
        # Clics comptés en mémoire pendant une panne Redis : ajoutés aux chiffres
        # Redis au lieu d'être ignorés.
        with self._lock:
            counts = Counter(self._memory.get(month, Counter()))
        if self.redis is not None:
            try:
                raw = self.redis.hgetall(_PREFIX + month) or {}
                counts.update({str(k): int(v) for k, v in raw.items()})
            except Exception:
                if self.logger is not None:
                    self.logger.warning("click-stats redis illisible")
        return counts

    def summary(self, months: int = 6, today: _dt.date | None = None) -> list[dict]:
        """[{month, total, by_kind: {kind: n}, rows: [(kind, source, n)]}] du plus récent au plus ancien."""
        out = []
        for month in _previous_months(months, today):
            counts = self.month_counts(month)
            by_kind: Counter = Counter()
            rows = []
            for field, n in counts.items():
                kind, _, source = field.partition("|")
                by_kind[kind] += n
                rows.append((kind, source, n))
            rows.sort(key=lambda row: (-row[2], row[0], row[1]))
            out.append({"month": month, "total": sum(by_kind.values()), "by_kind": dict(by_kind), "rows": rows})
        return out
