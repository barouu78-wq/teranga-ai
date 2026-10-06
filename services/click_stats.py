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

    def record(self, kind: str, source: str, day: _dt.date | None = None) -> None:
        field = f"{kind}|{source or '-'}"
        month = _month(day)
        if self.redis is not None:
            try:
                key = _PREFIX + month
                self.redis.hincrby(key, field, 1)
                self.redis.expire(key, _KEEP_SECONDS)
                return
            except Exception:
                if self.logger is not None:
                    self.logger.warning("click-stats redis indisponible, comptage en mémoire")
        with self._lock:
            self._memory.setdefault(month, Counter())[field] += 1

    def month_counts(self, month: str) -> Counter:
        if self.redis is not None:
            try:
                raw = self.redis.hgetall(_PREFIX + month) or {}
                return Counter({str(k): int(v) for k, v in raw.items()})
            except Exception:
                if self.logger is not None:
                    self.logger.warning("click-stats redis illisible")
        with self._lock:
            return Counter(self._memory.get(month, Counter()))

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
