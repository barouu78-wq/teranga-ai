"""Lightweight intent and context extraction for Teranga AI.

The engine is deterministic and now resolves short follow-ups from recent
conversation context without changing the user's original query.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from .senegal_knowledge import classify_domain, needs_fresh_web, source_domains


SUPPORTED_LANGUAGES = ("fr", "en", "wo", "ff")

_INTENT_PATTERNS = {
    "trip_planning": (
        "voyage", "trip", "itineraire", "itinéraire", "programme",
        "sejour", "séjour", "vacances", "planifier", "planning",
    ),
    "weather": ("meteo", "météo", "weather", "temps"),
    "transport": (
        "transport", "bus", "taxi", "car", "aeroport", "aéroport",
        "airport", "ter", "train",
    ),
    "restaurant": ("restaurant", "manger", "eat", "cuisine", "plat", "plats"),
    "photos": (
        "photo", "photos", "image", "images", "visuel", "visuels",
        "montre-moi", "montre moi", "a quoi ressemble", "à quoi ça ressemble",
    ),
    "culture": ("culture", "tradition", "histoire", "history", "musique"),
}

_DYNAMIC_INTENTS = {"trip_planning", "weather", "transport", "restaurant", "photos"}

_LOCATION_ALIASES = {
    "dakar": ("dakar",),
    "goree": ("goree", "gorée", "ile de goree", "île de gorée"),
    "saint-louis": ("saint-louis", "saint louis"),
    "lac rose": ("lac rose", "lake retba", "retba"),
    "casamance": ("casamance",),
    "senegal": ("senegal", "sénégal"),
    "thies": ("thies", "thiès"),
    "diourbel": ("diourbel",),
    "fatick": ("fatick",),
    "kaolack": ("kaolack",),
    "kaffrine": ("kaffrine",),
    "louga": ("louga",),
    "matam": ("matam",),
    "tambacounda": ("tambacounda",),
    "kedougou": ("kedougou", "kédougou"),
    "kolda": ("kolda",),
    "sedhiou": ("sedhiou", "sédhiou"),
    "ziguinchor": ("ziguinchor",),
    "touba": ("touba",),
    "mbour": ("mbour",),
    "saly": ("saly",),
    "tivaouane": ("tivaouane",),
    "joal-fadiouth": ("joal-fadiouth", "joal", "fadiouth"),
    "cap skirring": ("cap skirring",),
    "podor": ("podor",),
    "richard-toll": ("richard-toll", "richard toll"),
    "ourossogui": ("ourossogui",),
    "dindefelo": ("dindefelo", "dindéfello", "dindéfelo"),
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def detect_language(text: str) -> str:
    normalized = _normalize(text)
    if any(word in normalized.split() for word in ("hello", "please", "where", "what", "travel")):
        return "en"
    if any(word in normalized.split() for word in ("nanga", "jamm", "fan", "lan")):
        return "wo"
    if any(word in normalized.split() for word in ("a", "hol", "ko", "mi")) and "senegal" not in normalized:
        return "ff"
    return "fr"


def detect_intent(text: str) -> str:
    normalized = _normalize(text)
    for intent, patterns in _INTENT_PATTERNS.items():
        if any(_normalize(pattern) in normalized for pattern in patterns):
            return intent
    return "general_information"


def detect_location(text: str) -> str | None:
    normalized = _normalize(text)
    for location, aliases in _LOCATION_ALIASES.items():
        if any(_normalize(alias) in normalized for alias in aliases):
            return location
    return None


def _recent_user_messages(history: list[dict[str, Any]] | None, limit: int = 6) -> list[str]:
    messages: list[str] = []
    for item in reversed(history or []):
        if not isinstance(item, dict) or item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content:
            messages.append(content)
        if len(messages) >= limit:
            break
    return messages


def build_intent_context(text: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    message = str(text or "").strip()
    current_intent = detect_intent(message)
    current_location = detect_location(message)
    recent_users = _recent_user_messages(history)
    resolved_intent = current_intent
    resolved_location = current_location
    context_source = "current_message"
    if recent_users:
        if resolved_intent == "general_information":
            for previous in recent_users:
                previous_intent = detect_intent(previous)
                if previous_intent != "general_information":
                    resolved_intent = previous_intent
                    context_source = "conversation"
                    break
        if resolved_location is None:
            for previous in recent_users:
                previous_location = detect_location(previous)
                if previous_location is not None:
                    resolved_location = previous_location
                    context_source = "conversation"
                    break
    domain = classify_domain(message)
    fresh = needs_fresh_web(domain, message) or resolved_intent in _DYNAMIC_INTENTS
    return {
        "intent": resolved_intent,
        "domain": domain,
        "location": resolved_location,
        "language": detect_language(message),
        "needs_web_search": fresh,
        "needs_images": resolved_intent == "photos",
        "preferred_sources": source_domains(domain),
        "has_context": bool(recent_users),
        "context_source": context_source,
        "query": message,
        "normalized_query": _normalize(message),
    }
