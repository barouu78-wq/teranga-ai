"""Réponse de secours quand l'IA est indisponible (panne, quota, délai dépassé).

Plutôt qu'un simple message d'erreur, Teranga répond avec sa propre base de
connaissances quand la question cite un lieu ou un plat connu. Texte brut :
le chat l'affiche tel quel.
"""

from __future__ import annotations

import re

from services.places import mentioned_places
from services.senegal_knowledge import _fold

_INTRO = {
    "fr": "L'assistant IA est momentanément indisponible. Voici ce que je sais déjà :",
    "en": "The AI assistant is temporarily unavailable. Here is what I already know (in French):",
}
_OUTRO = {
    "fr": "Réessaie dans un moment pour une réponse complète et personnalisée.",
    "en": "Please try again in a moment for a complete answer.",
}


def _first_sentences(text: str, count: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    return " ".join(parts[:count]).strip()


def _place_text(place: dict) -> str:
    lines = [f"{place.get('name', '')} ({place.get('region', '')}) : {place.get('summary', '')}".strip()]
    history = _first_sentences(place.get("history", ""))
    if history and history not in lines[0]:
        lines.append(history)
    what = [item.strip() for item in str(place.get("what_to_see", "")).split(";") if item.strip()]
    if what:
        lines.append("À voir : " + ", ".join(what) + ".")
    if place.get("access"):
        lines.append("Comment y aller : " + str(place["access"]))
    return "\n".join(lines)


def _matched_dish(dishes, message: str) -> dict | None:
    folded = _fold(message)
    for dish in dishes or []:
        pattern = dish.get("_match") if isinstance(dish, dict) else None
        if pattern is not None and pattern.search(folded):
            return dish
    return None


def knowledge_fallback(message: str, places, dishes=(), lang: str = "fr") -> str | None:
    """Réponse tirée de la base pour un lieu ou un plat cité ; None sinon."""
    lang = "en" if lang == "en" else "fr"
    found = mentioned_places(message, places or [], limit=1)
    by_id = {str(p.get("id")): p for p in places or [] if isinstance(p, dict)}
    body = ""
    if found:
        body = _place_text(by_id.get(found[0]["id"], found[0]))
    else:
        dish = _matched_dish(dishes, message)
        if dish:
            where = f" Où : {dish['where']}." if dish.get("where") else ""
            body = f"{dish.get('name')} : {dish.get('text')}{where}"
    if not body:
        return None
    return f"{_INTRO[lang]}\n\n{body}\n\n{_OUTRO[lang]}"
