"""Lightweight intent and context extraction for Teranga AI.

The engine is deterministic and now resolves short follow-ups from recent
conversation context without changing the user's original query.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from .senegal_knowledge import REGION_ALIASES, REGION_HIGHLIGHTS, classify_domain, needs_fresh_web, source_domains
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
    "project": ("projet", "business", "entreprise", "entreprendre", "entrepreneur", "activité", "activite", "commerce", "lancer", "vendre", "clients", "clientèle", "clientele"),
    "career": ("emploi", "travail", "job", "cv", "recrutement", "carrière", "carriere", "embauche", "métier", "metier"),
    "education": ("formation", "étudier", "etudier", "école", "ecole", "université", "universite", "apprendre", "cours", "étudiant", "etudiant"),
    "finance": ("argent", "financement", "budget", "revenus", "salaire", "épargne", "epargne", "investir", "crédit", "credit", "prêt", "pret"),
}

_DYNAMIC_INTENTS = {"trip_planning", "weather", "transport", "restaurant", "photos", "career", "finance", "project"}

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


_NORMALIZED_INTENT_PATTERNS = {
    intent: tuple(_normalize(pattern) for pattern in patterns)
    for intent, patterns in _INTENT_PATTERNS.items()
}
_NORMALIZED_LOCATION_ALIASES = {
    location: tuple(_normalize(alias) for alias in aliases)
    for location, aliases in _LOCATION_ALIASES.items()
}

_CONTEXT_CITIES = (
    "dakar", "thies", "thiès", "mbour", "saly", "somone", "touba",
    "kaolack", "fatick", "saint-louis", "saint louis", "louga", "matam",
    "podor", "richard-toll", "ziguinchor", "cap skirring", "kolda",
    "sedhiou", "sédhiou", "tambacounda", "kedougou", "kédougou",
    "rufisque", "pikine", "guediawaye", "guédiawaye", "diamniadio",
    "ngor", "yoff", "ouakam", "alhadies", "almalies", "almaties",
    "almadies", "aibd", "goree", "gorée", "lac rose", "saloum", "casamance",
)
_CONTEXT_REGIONS = (
    "dakar", "thiès", "thies", "diourbel", "fatick", "kaolack", "kaffrine",
    "tambacounda", "kédougou", "kedougou", "kolda", "sédhiou", "sedhiou",
    "ziguinchor", "saint-louis", "louga", "matam",
)
_CONTEXT_ALIASES = {
    "aeroport blaise diagne": "aibd", "aéroport blaise diagne": "aibd",
    "ile de goree": "goree", "île de gorée": "goree",
    "goree": "goree", "gorée": "goree", "lac rose": "lac rose",
    "alhadies": "almadies", "almalies": "almadies", "almaties": "almadies",
}

def _contains_term(text: str, term: str) -> bool:
    if " " in term or "-" in term:
        return term in text
    return bool(re.search(r"(?<!\\w)" + re.escape(term) + r"(?!\\w)", text))

_CONTEXT_INTENT_GROUPS = {
    "weather": ("meteo", "météo", "pluie", "temperature", "température", "vent", "chaleur"),
    "transport": ("trajet", "itineraire", "itinéraire", "taxi", "bus", "ferry", "vol", "aeroport", "aéroport", "transport", "route"),
    "food": ("restaurant", "manger", "repas", "plat", "ceebu", "thiéb", "yassa", "mafe", "dibi"),
    "price": ("prix", "tarif", "cout", "coût", "combien", "budget", "fcfa", "cfa"),
    "travel": ("voyage", "visiter", "séjour", "sejour", "tourisme", "vacances", "plage", "goree", "gorée"),
    "admin": ("visa", "passeport", "formalites", "formalités", "demarche", "démarche", "document"),
    "money": ("change", "taux", "euro", "dollar", "livre sterling", "orange money", "wave", "transfert"),
    "culture": ("culture", "histoire", "langue", "wolof", "pulaar", "tradition", "musique", "teranga"),
    "news": ("actualite", "actualités", "news", "nouveau", "nouvelle", "aujourd'hui", "demain"),
    "project": ("projet", "business", "entreprise", "entreprendre", "entrepreneur", "activité", "activite", "commerce", "clients", "vendre", "lancer"),
    "career": ("emploi", "travail", "job", "cv", "recrutement", "carriere", "carrière", "embauche", "metier", "métier"),
    "education": ("formation", "étudier", "etudier", "école", "ecole", "université", "universite", "apprendre", "cours", "étudiant", "etudiant"),
    "finance": ("argent", "financement", "budget", "revenus", "salaire", "épargne", "epargne", "investir", "crédit", "credit", "prêt", "pret"),
}


def detect_language(text: str) -> str:
    normalized = _normalize(text)
    english_markers = ("hello", "please", "where", "what", "how", "why", "travel", "visit", "want", "can", "could", "would")
    tokens = set(normalized.split())
    if any(word in tokens for word in english_markers) or normalized.startswith(("i ", "we ", "can ")):
        return "en"
    if any(word in normalized.split() for word in ("nanga", "jamm", "fan", "lan")):
        return "wo"
    if any(word in normalized.split() for word in ("hol", "ko", "mi")) and "senegal" not in normalized:
        return "ff"
    return "fr"


def detect_intent(text: str) -> str:
    normalized = _normalize(text)
    for intent, patterns in _NORMALIZED_INTENT_PATTERNS.items():
        if any(re.search(r"(?<!\w)" + re.escape(pattern) + r"(?!\w)", normalized) for pattern in patterns):
            return intent
    return "general_information"


def detect_location(text: str) -> str | None:
    normalized = _normalize(text)
    for location, aliases in _NORMALIZED_LOCATION_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return location
    for region, aliases in REGION_ALIASES.items():
        if any(_normalize(alias) in normalized for alias in aliases):
            return _normalize(region)
    for region, places in REGION_HIGHLIGHTS.items():
        for place in places:
            if _normalize(place) in normalized:
                return _normalize(place)
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
    normalized_place_text = text_value
    for alias, canonical in _CONTEXT_ALIASES.items():
        if _normalize(alias) in normalized_place_text:
            normalized_place_text += " " + canonical
    found_cities = [x for x in _CONTEXT_CITIES if x in normalized_place_text]
    found_regions = [x for x in _CONTEXT_REGIONS if x in normalized_place_text]
    intents = [name for name, terms in _CONTEXT_INTENT_GROUPS.items() if any(_contains_term(text_value, term) for term in terms)]
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
        bool(intents.intersection({"travel", "transport", "food"}))
        and (bool(context.get("duration")) or bool(context.get("budget")) or any(term in query for term in planning_terms))
    )


def should_use_deep_reasoning(context: dict[str, Any]) -> bool:
    """Detect requests where extra reasoning is useful beyond trip planning."""
    query = _normalize(str(context.get("query") or ""))
    intents = set(context.get("intents") or [])
    constraints = context.get("constraints") or []
    multi_step_terms = (
        "compare", "comparatif", "difference", "choisir", "quel est le meilleur",
        "avantages", "inconvenients", "pourquoi", "comment faire", "etape",
        "plan", "organise", "optimise", "priorite", "versus", "vs",
    )
    complex_intents = {"travel", "transport", "price", "money", "admin", "food", "project", "career", "education", "finance"}
    decision_intents = {"project", "career", "education", "finance"}
    return (
        len(constraints) >= 2
        or (len(intents.intersection(complex_intents)) >= 2)
        or (bool(intents.intersection(decision_intents)) and bool(constraints))
        or any(re.search(r"\b" + re.escape(term) + r"\b", query) for term in multi_step_terms)
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
    if "semaine" in duration_raw:
        duration_days = duration_days * 7 if duration_days is not None else 7
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

def build_intent_context(text: str, history: list[dict[str, Any]] | None = None, *, resolved_context: dict[str, Any] | None = None) -> dict[str, Any]:
    message = str(text or "").strip()
    current_intent = detect_intent(message)
    current_location = detect_location(message)
    recent_users = _recent_user_messages(history)
    resolved_intent = current_intent
    resolved_location = current_location
    context_source = "current_message"
    if recent_users:
        follow_up_markers = ("et ", "et pour", "et le", "et la", "et les", "ça", "cela", "ce sujet", "pour le budget", "combien", "quel prix", "qu'en est-il")
        is_short_follow_up = len(message.split()) <= 8 and (
            _normalize(message).startswith(tuple(_normalize(marker) for marker in follow_up_markers))
            or "?" in message
        )
        if resolved_intent == "general_information" or is_short_follow_up:
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
    context_data = resolved_context if resolved_context is not None else infer_senegal_context(history, message)
    context_query = str(context_data.get("query") or "") or contextual_query(history, message)
    domain = classify_domain(context_query)
    fresh = needs_fresh_web(domain, context_query) or resolved_intent in _DYNAMIC_INTENTS
    return {
        "intent": resolved_intent,
        "domain": domain,
        "location": resolved_location,
        "language": detect_language(message),
        "needs_web_search": fresh,
        "needs_images": resolved_intent == "photos",
        "needs_deep_reasoning": should_use_deep_reasoning({
            "query": context_query,
            "intents": [resolved_intent],
            "constraints": context_data.get("constraints", []),
        }),
        "preferred_sources": source_domains(domain),
        "has_context": bool(recent_users),
        "context_source": context_source,
        "query": message,
        "normalized_query": _normalize(message),
    }
