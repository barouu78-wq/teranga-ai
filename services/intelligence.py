"""Lightweight intent and context extraction for Teranga AI.

This first version is deliberately deterministic: it normalizes a user message
into a small routing context without changing the existing chat behavior.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


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

_LOCATION_ALIASES = {
    "dakar": ("dakar",),
    "goree": ("goree", "gorée", "ile de goree", "île de gorée"),
    "saint-louis": ("saint-louis", "saint louis"),
    "lac rose": ("lac rose", "lake retba", "retba"),
    "casamance": ("casamance",),
    "senegal": ("senegal", "sénégal"),
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


def build_intent_context(text: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    message = str(text or "").strip()
    intent = detect_intent(message)
    location = detect_location(message)
    normalized = _normalize(message)
    needs_web = intent in {"trip_planning", "weather", "transport", "restaurant", "photos"}
    needs_images = intent == "photos"
    return {
        "intent": intent,
        "location": location,
        "language": detect_language(message),
        "needs_web_search": needs_web,
        "needs_images": needs_images,
        "has_context": bool(history),
        "query": message,
        "normalized_query": normalized,
    }
