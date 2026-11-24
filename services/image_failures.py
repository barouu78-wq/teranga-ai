"""Échecs du proxy d'images (/image-proxy) : cause, réponse au navigateur et souvenir borné.

Avant le 22 novembre 2026, toute erreur donnait le même 502 et le même journal (« Erreur proxy image Wikimedia » avec
la trace complète), et une image cassée était redemandée à Wikimedia à chaque affichage. Ici :
- chaque cause connue a son nom, sa réponse et un journal d'une ligne (sans adresse de visiteur) ;
- un échec est gardé quelques minutes, par processus et en nombre limité : on n'insiste pas auprès de Wikimedia
  (surtout après un refus « trop de demandes ») et le journal ne se remplit pas en rafale.
"""

from __future__ import annotations

import socket
import threading
import time
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

# Cause → (statut renvoyé au navigateur, message)
RESPONSES = {
    "introuvable": (404, "Image introuvable"),
    "limite": (503, "Source d'images momentanément saturée. Réessaie plus tard."),
    "erreur-source": (502, "Image indisponible"),
    "delai": (504, "Image trop lente à charger"),
    "reseau": (502, "Image indisponible"),
    "type": (502, "Image indisponible"),
    "trop-lourde": (502, "Image indisponible"),
    "redirection": (502, "Image indisponible"),
    "inattendue": (502, "Image indisponible"),
}

# Durée du souvenir d'un échec, en secondes : long pour un défaut qui ne change pas (image absente, mauvais type),
# court pour un incident passager (délai, réseau, erreur du serveur source).
TTL = {
    "introuvable": 3600,
    "type": 3600,
    "trop-lourde": 3600,
    "redirection": 3600,
    "erreur-source": 120,
    "delai": 60,
    "reseau": 60,
    "inattendue": 60,
    # « limite » : le délai demandé par Wikimedia (Retry-After), borné.
}
RETRY_AFTER_DEFAULT = 60
RETRY_AFTER_MAX = 300
MAX_ENTRIES = 512

_lock = threading.Lock()
_failures: OrderedDict[str, tuple[float, str, int]] = OrderedDict()


def _now() -> float:
    return time.monotonic()


def _retry_after(exc: HTTPError) -> int:
    raw = str((getattr(exc, "headers", None) or {}).get("Retry-After", "") or "").strip()
    seconds = int(raw) if raw.isdigit() else RETRY_AFTER_DEFAULT
    return max(1, min(seconds, RETRY_AFTER_MAX))


def _is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, (socket.timeout, TimeoutError))


def classify(exc: BaseException) -> tuple[str, int]:
    """(cause, délai d'attente en secondes, 0 sans objet) d'une erreur de safe_image_fetch."""
    if isinstance(exc, HTTPError):
        if exc.code in (404, 410):
            return "introuvable", 0
        if exc.code == 429:
            return "limite", _retry_after(exc)
        return "erreur-source", 0
    if _is_timeout(exc) or (isinstance(exc, URLError) and _is_timeout(getattr(exc, "reason", None))):
        return "delai", 0
    if isinstance(exc, (URLError, ConnectionError, OSError)):
        return "reseau", 0
    if isinstance(exc, ValueError):
        message = str(exc)
        if "Type image" in message:
            return "type", 0
        if "volumineuse" in message:
            return "trop-lourde", 0
        if "Redirection" in message:
            return "redirection", 0
    return "inattendue", 0


def remember(src: str, kind: str, retry_after: int = 0) -> None:
    ttl = retry_after if kind == "limite" else TTL.get(kind, 60)
    with _lock:
        _failures[src] = (_now() + ttl, kind, retry_after)
        _failures.move_to_end(src)
        while len(_failures) > MAX_ENTRIES:
            _failures.popitem(last=False)


def recall(src: str) -> tuple[str, int] | None:
    """(cause, délai restant) si cette image a échoué récemment, sinon None."""
    with _lock:
        entry = _failures.get(src)
        if not entry:
            return None
        expires, kind, _retry = entry
        remaining = expires - _now()
        if remaining <= 0:
            del _failures[src]
            return None
    return kind, max(1, int(remaining)) if kind == "limite" else 0


def size() -> int:
    with _lock:
        return len(_failures)


def reset() -> None:
    with _lock:
        _failures.clear()


def log_line(src: str, kind: str, elapsed_ms: int, exc: BaseException) -> str:
    """Une ligne de journal : cause, code HTTP de la source, hôte, nom du fichier (public), durée. Jamais d'adresse
    de visiteur ni de paramètre de requête."""
    parsed = urlparse(src)
    name = parsed.path.rsplit("/", 1)[-1][:80]
    code = f" http={exc.code}" if isinstance(exc, HTTPError) else ""
    return f"proxy image : cause={kind}{code} hote={parsed.hostname or '?'} fichier={name} duree={elapsed_ms} ms"
