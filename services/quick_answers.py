"""Réponses prêtes aux questions fréquentes, servies sans appeler le modèle.

Une question courte qui ne demande que les numéros d'urgence (« Numéro de la police ? ») reçoit tout
de suite les numéros vérifiés de la page /urgences (routes/emergency.py, source : ambassade de France au
Sénégal, relevés le 6 octobre 2026). Seuls 17, 18 et 1515 sont servis : la gendarmerie et SOS Médecins
sont à revérifier. Toute autre formulation (une situation, un lieu, une précision) va au modèle.
"""

from __future__ import annotations

import re
from typing import Any

from routes.emergency import ADVICE, EMBASSY_LINKS, EMERGENCY_NUMBERS
from services.answer_cache import _has_earlier_turns
from services.text import fold_text

MAX_CHARS = 80
_NUMBER_WORDS = {"numero", "numeros", "num", "tel", "telephone", "appeler", "number", "numbers", "call"}
_SERVICE_WORDS = {"urgence", "urgences", "police", "pompier", "pompiers", "samu", "secours",
                  "emergency", "emergencies", "ambulance"}
# Mots qui ne changent pas la demande. Un mot hors de cette liste (un lieu précis, une situation) : le modèle répond.
_FILLER_WORDS = {
    "quel", "quels", "quelle", "quelles", "est", "sont", "c", "ce", "le", "la", "les", "l", "de", "d", "du", "des",
    "au", "a", "en", "pour", "qui", "cas", "s", "il", "te", "vous", "plait", "stp", "svp", "bonjour", "merci",
    "senegal", "dakar", "what", "is", "are", "the", "in", "for", "who", "to", "please", "hi", "hello",
    "fire", "brigade", "department", "service", "services", "medical", "medicale",
}
_ALLOWED = _NUMBER_WORDS | _SERVICE_WORDS | _FILLER_WORDS
_LABELS_EN = {"17": "Police", "18": "Fire brigade", "1515": "SAMU (medical emergency)"}
_SOURCES = [{"title": "Ambassade de France au Sénégal", "url": EMBASSY_LINKS[0][1]}]


def _asks_emergency_numbers(message: str) -> bool:
    if len(message) > MAX_CHARS:
        return False
    words = re.findall(r"[a-z0-9]+", fold_text(message).lower())
    return (
        bool(words)
        and set(words) <= _ALLOWED
        and bool(_SERVICE_WORDS.intersection(words))
        and bool(_NUMBER_WORDS.intersection(words))
    )


def _emergency_reply(language: str) -> str:
    national = [entry for entry in EMERGENCY_NUMBERS if entry[0] in _LABELS_EN]
    if language == "en":
        lines = ["Emergency numbers in Senegal, free from any phone, even without credit:"]
        lines += [f"- {_LABELS_EN[shown]}: {shown}" for shown, _, _, _ in national]
        lines += ["", "Give the exact place first (neighbourhood, landmark, hotel name), then what is happening.",
                  "All useful numbers, readable offline: teranga-ai.fr/urgences"]
    else:
        lines = ["Numéros d'urgence au Sénégal, gratuits depuis tous les téléphones, même sans crédit :"]
        lines += [f"- {service} : {shown}" for shown, _, service, _ in national]
        lines += ["", ADVICE[1], "Tous les numéros utiles, lisibles hors connexion : teranga-ai.fr/urgences"]
    return "\n".join(lines)


def quick_answer(payload: dict[str, Any], raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Réponse prête ({reply, sources}) au format du cache des réponses, ou None (le modèle répond)."""
    raw = raw if isinstance(raw, dict) else {}
    language = str(payload.get("language") or "fr")
    message = str(payload.get("message") or "")
    if language not in ("fr", "en") or payload.get("photo_only"):
        return None
    if _has_earlier_turns(raw.get("history"), message):
        return None
    if any(str(raw.get(name) or "").strip() for name in ("context_place", "trip_context", "trip_edit_request")):
        return None
    if not _asks_emergency_numbers(message):
        return None
    return {"reply": _emergency_reply(language), "sources": list(_SOURCES), "image": None, "map": None}
