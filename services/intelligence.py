"""Lightweight intent and context extraction for Teranga AI.

The engine is deterministic and now resolves short follow-ups from recent
conversation context without changing the user's original query.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from .senegal_knowledge import REGION_ALIASES, classify_domain, needs_fresh_web, source_domains
from .validation import sanitize_text


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
    if any(word in normalized.split() for word in ("hol", "ko", "mi")) and "senegal" not in normalized:
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
    for region, aliases in REGION_ALIASES.items():
        if any(_normalize(alias) in normalized for alias in aliases):
            return _normalize(region)
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



def contextual_query(history: list[dict[str, Any]] | None, message: str, max_history_items: int = 12, max_message_length: int = 2000) -> str:
    """Build an internal context query from recent user turns."""
    parts: list[str] = []
    if isinstance(history, list):
        for item in history[-max_history_items:]:
            if not isinstance(item, dict) or str(item.get("role", "")).lower() != "user":
                continue
            content = sanitize_text(item.get("content", ""), 900)
            if content:
                parts.append(content)
    current = str(message or "").strip()[:max_message_length]
    recent = parts[-4:]
    if current:
        recent.append(current)
    return " | ".join(recent)[-5000:]


def infer_senegal_context(history: list[dict[str, Any]] | None, message: str) -> dict[str, Any]:
    """Resolve Senegal places, intents and planning constraints from recent turns."""
    context_query = contextual_query(history, message)
    text_value = _normalize(context_query)
    cities = (
        "dakar", "thies", "thiès", "mbour", "saly", "somone", "touba",
        "kaolack", "fatick", "saint-louis", "saint louis", "louga", "matam",
        "podor", "richard-toll", "ziguinchor", "cap skirring", "kolda",
        "sedhiou", "sédhiou", "tambacounda", "kedougou", "kédougou",
        "rufisque", "pikine", "guediawaye", "guédiawaye", "diamniadio",
        "ngor", "yoff", "ouakam", "alhadies", "almalies", "almaties",
        "almadies", "aibd", "goree", "gorée", "lac rose", "saloum", "casamance",
    )
    regions = (
        "dakar", "thiès", "thies", "diourbel", "fatick", "kaolack", "kaffrine",
        "tambacounda", "kédougou", "kedougou", "kolda", "sédhiou", "sedhiou",
        "ziguinchor", "saint-louis", "louga", "matam",
    )
    aliases = {
        "aeroport blaise diagne": "aibd", "aéroport blaise diagne": "aibd",
        "ile de goree": "goree", "île de gorée": "goree",
        "goree": "goree", "gorée": "goree", "lac rose": "lac rose",
        "alhadies": "almadies", "almalies": "almadies", "almaties": "almadies",
    }
    normalized_place_text = text_value
    for alias, canonical in aliases.items():
        if _normalize(alias) in normalized_place_text:
            normalized_place_text += " " + canonical
    found_cities = [x for x in cities if x in normalized_place_text]
    found_regions = [x for x in regions if x in normalized_place_text]
    intent_groups = {
        "weather": ("meteo", "météo", "pluie", "temperature", "température", "vent", "chaleur"),
        "transport": ("trajet", "itineraire", "itinéraire", "taxi", "bus", "ferry", "vol", "aeroport", "aéroport", "transport", "route"),
        "food": ("restaurant", "manger", "repas", "plat", "ceebu", "thiéb", "yassa", "mafe", "dibi"),
        "price": ("prix", "tarif", "cout", "coût", "combien", "budget", "fcfa", "cfa"),
        "travel": ("voyage", "visiter", "séjour", "sejour", "tourisme", "vacances", "plage", "goree", "gorée"),
        "admin": ("visa", "passeport", "formalites", "formalités", "demarche", "démarche", "document"),
        "money": ("change", "taux", "euro", "dollar", "livre sterling", "orange money", "wave", "transfert"),
        "culture": ("culture", "histoire", "langue", "wolof", "pulaar", "tradition", "musique", "teranga"),
        "news": ("actualite", "actualités", "news", "nouveau", "nouvelle", "aujourd'hui", "demain"),
    }
    intents = [name for name, terms in intent_groups.items() if any(term in text_value for term in terms)]
    currency_amounts = re.findall(
        r"(?<![\w])(?:\d[\d\s.,]*)\s*(?:fcfa|f cfa|cfa|€|euros?|dollars?|\$)",
        text_value,
    )
    amounts = re.findall(r"(?<![\w])(?:\d[\d\s.,]*)(?:\s*(?:fcfa|f cfa|cfa|€|euros?|dollars?|\$))?(?!\s*(?:jour|jours|semaine|semaines|nuit|nuits)\b)", text_value)
    budget = (currency_amounts[-1] if currency_amounts else amounts[-1].strip() if amounts else "")
    duration_match = re.search(r"\b(\d+)\s*(jour|jours|semaine|semaines|nuit|nuits)\b", text_value)
    duration = duration_match.group(0) if duration_match else ""
    adults_match = re.search(r"\b(\d+)\s*(?:adultes?|personnes?)(?:\s*\+\s*(\d+)\s*enfants?)?\b", text_value)
    children_match = re.search(r"\b(\d+)\s*enfants?\b", text_value)
    adults = int(adults_match.group(1)) if adults_match else None
    children = int(adults_match.group(2)) if adults_match and adults_match.group(2) else (
        int(children_match.group(1)) if children_match else None
    )
    if "en famille" in text_value and children is None:
        children = 1

    constraints = []
    if budget:
        constraints.append("budget=" + budget)
    if duration:
        constraints.append("durée=" + duration)
    if adults is not None:
        constraints.append("adultes=" + str(adults))
    if children is not None:
        constraints.append("enfants=" + str(children))
    if "avec mes enfants" in text_value or "en famille" in text_value:
        constraints.append("famille")
    if "ce soir" in text_value:
        constraints.append("ce soir")
    if "demain" in text_value:
        constraints.append("demain")
    place = found_cities[-1] if found_cities else (found_regions[-1] if found_regions else "")
    return {
        "place": place,
        "has_place": bool(found_cities or found_regions),
        "query": text_value,
        "intents": intents[:4],
        "constraints": constraints[:8],
        "budget": budget,
        "duration": duration,
        "adults": adults,
        "children": children,
        "context_source": "conversation" if history and message and len(text_value) > len(_normalize(message)) else "current_message",
    }


def should_use_planner(context: dict[str, Any]) -> bool:
    """Detect a multi-step planning request without forcing web search."""
    intents = set(context.get("intents", []))
    query = context.get("query", "")
    planning_terms = (
        "planifie", "programme", "organise", "itineraire", "itinéraire",
        "journee", "journée", "sejour", "séjour", "vacances", "weekend",
        "week-end", "pendant", "pour 2 jours", "pour 3 jours", "pour 4 jours",
        "pour 5 jours", "pour une semaine", "budget",
    )
    return (
        bool(intents.intersection({"travel", "transport", "food", "price"}))
        and (bool(context.get("duration")) or bool(context.get("budget")) or any(term in query for term in planning_terms))
    )


def build_planner_data(context: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic brief for plans and their budgets."""
    budget_raw = context.get("budget", "")
    budget_match = re.search(r"(\d[\d\s.,]*)", budget_raw or "")
    budget_amount = None
    if budget_match:
        raw = re.sub(r"[\s.,]", "", budget_match.group(1))
        try:
            budget_amount = int(raw)
        except ValueError:
            budget_amount = None
    duration_raw = context.get("duration", "")
    duration_days = None
    duration_match = re.search(r"(\d+)", duration_raw or "")
    if duration_match:
        try:
            duration_days = int(duration_match.group(1))
        except ValueError:
            duration_days = None
    if duration_days is None and "semaine" in duration_raw:
        duration_days = 7
    return {
        "place": context.get("place", ""),
        "duration": duration_raw,
        "duration_days": duration_days,
        "budget_raw": budget_raw,
        "budget_fcfa": budget_amount,
        "intents": context.get("intents", []),
        "constraints": context.get("constraints", []),
        "adults": context.get("adults"),
        "children": context.get("children"),
        "family": "famille" in context.get("constraints", []),
    }

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
    context_query = contextual_query(history, message)
    domain = classify_domain(context_query)
    fresh = needs_fresh_web(domain, context_query) or resolved_intent in _DYNAMIC_INTENTS
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
