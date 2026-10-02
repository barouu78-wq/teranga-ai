"""Senegal-first knowledge and retrieval policy for Teranga AI.

This module does not pretend to be a static encyclopedia. It gives the response
engine a structured map of Senegal topics and source priorities so it can decide
when fresh web evidence is required.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Official administrative coverage: all 14 regions of Senegal.
SENEGAL_REGIONS = (
    "Dakar", "Diourbel", "Fatick", "Kaffrine", "Kaolack", "Kédougou", "Kolda",
    "Louga", "Matam", "Saint-Louis", "Sédhiou", "Tambacounda", "Thiès", "Ziguinchor",
)

REGION_ALIASES = {
    "Dakar": ("dakar",), "Diourbel": ("diourbel",), "Fatick": ("fatick",),
    "Kaffrine": ("kaffrine",), "Kaolack": ("kaolack",),
    "Kédougou": ("kedougou", "kédougou"), "Kolda": ("kolda",), "Louga": ("louga",),
    "Matam": ("matam",), "Saint-Louis": ("saint-louis", "saint louis"),
    "Sédhiou": ("sedhiou", "sédhiou"), "Tambacounda": ("tambacounda",),
    "Thiès": ("thies", "thiès"), "Ziguinchor": ("ziguinchor",),
}

REGION_HIGHLIGHTS = {
    "Dakar": ("Dakar", "Gorée", "Rufisque", "Ngor", "Yoff", "Ouakam"),
    "Thiès": ("Thiès", "Tivaouane", "Mbour", "Saly", "Joal-Fadiouth", "Popenguine"),
    "Diourbel": ("Diourbel", "Touba", "Mbacké"),
    "Fatick": ("Fatick", "Foundiougne", "Sokone", "Delta du Saloum"),
    "Kaolack": ("Kaolack", "Nioro du Rip", "Médina Baye"),
    "Kaffrine": ("Kaffrine", "Koungheul", "Birkelane"),
    "Louga": ("Louga", "Linguère", "Dahra", "Ferlo"),
    "Saint-Louis": ("Saint-Louis", "Podor", "Richard-Toll", "Djoudj"),
    "Matam": ("Matam", "Ourossogui", "Kanel", "Thilogne"),
    "Tambacounda": ("Tambacounda", "Bakel", "Niokolo-Koba"),
    "Kédougou": ("Kédougou", "Dindéfelo", "Bandafassi", "Pays Bassari"),
    "Kolda": ("Kolda", "Vélingara", "Haute-Casamance"),
    "Sédhiou": ("Sédhiou", "Bounkiling", "Goudomp", "Moyenne-Casamance"),
    "Ziguinchor": ("Ziguinchor", "Oussouye", "Cap Skirring", "Carabane"),
}

def region_highlights(region: str) -> tuple[str, ...]:
    return REGION_HIGHLIGHTS.get(str(region or ""), ())

SOURCE_PRIORITY = (
    "gov.sn",
    "ansd.sn",
    "tourisme.gouv.sn",
    "diplomatie.gouv.sn",
    "sante.gouv.sn",
    "education.gouv.sn",
    "interieur.gouv.sn",
    "transports.gouv.sn",
    "unesco.org",
    "who.int",
    "worldbank.org",
)

SENEGAL_DOMAINS = {
    "agriculture": ("agriculture", "élevage", "pêche", "horticulture"),
    "territory": ("régions", "départements", "communes", "villes", "géographie"),
    "travel": ("voyage", "tourisme", "itinéraire", "visiter", "plage", "hôtel"),
    "transport": ("transport", "TER", "BRT", "bus", "taxi", "aéroport", "AIBD"),
    "culture": ("culture", "histoire", "patrimoine", "musique", "tradition", "art"),
    "food": ("cuisine", "restaurant", "plat", "thieboudienne", "yassa", "mafé"),
    "economy": ("économie", "emploi", "prix", "entreprise", "commerce", "PIB", "business", "entrepreneur", "entreprendre"),
    "education": ("éducation", "formation", "école", "université", "apprendre", "cours", "étudiant"),
    "employment": ("emploi", "recrutement", "embauche", "carrière", "métier", "cv"),
    "society": ("population", "éducation", "santé", "emploi", "démographie"),
    "environment": ("environnement", "parc", "faune", "forêt", "climat"),
    "diaspora": ("diaspora", "Sénégal-France", "retour", "transfert"),
    "administration": ("démarche", "document", "visa", "administration", "consulat"),
    "business": ("business", "entreprise", "commerce", "entrepreneur", "entreprendre", "clients", "vente"),
}

DYNAMIC_DOMAINS = {
    "weather", "transport", "restaurant", "travel", "administration", "business", "employment", "education",
    "prices", "events", "news", "flights",
}

def _contains_domain_term(value: str, term: str) -> bool:
    normalized = str(term or "").casefold().strip()
    if not normalized:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized) + r"(?!\w)"
    return bool(re.search(pattern, value))


def classify_domain(text: str) -> str:
    value = str(text or "").casefold()
    if any(_contains_domain_term(value, term) for term in ("météo", "meteo", "weather", "pluie", "température", "temperature")):
        return "weather"
    for domain, terms in SENEGAL_DOMAINS.items():
        if any(_contains_domain_term(value, term) for term in terms):
            return domain
    return "general"

def needs_fresh_web(domain: str, text: str) -> bool:
    value = str(text or "").lower()
    return domain in DYNAMIC_DOMAINS or any(
        marker in value for marker in ("aujourd", "maintenant", "actuel", "latest",
                                       "cette semaine", "prix", "ouvert", "horaires")
    )

def source_domains(domain: str) -> tuple[str, ...]:
    if domain in {"society", "economy", "agriculture", "territory", "business", "employment", "education"}:
        return SOURCE_PRIORITY
    if domain in {"travel", "culture", "environment"}:
        return ("tourisme.gouv.sn", "ansd.sn", "unesco.org", "gov.sn")
    if domain == "administration":
        return ("diplomatie.gouv.sn", "interieur.gouv.sn", "gov.sn")
    if domain == "weather":
        return ("meteofrance.com", "ansd.sn", "gov.sn")
    if domain == "transport":
        return ("transports.gouv.sn", "gov.sn", "ansd.sn")
    if domain == "food":
        return ("agriculture.gouv.sn", "tourisme.gouv.sn", "gov.sn")
    return SOURCE_PRIORITY

def load_senegal_people(path: Path | None = None) -> list[dict]:
    path = path or Path(__file__).resolve().parents[1] / "data" / "senegal_people.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        people = data.get("people", []) if isinstance(data, dict) else []
        return people if isinstance(people, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def load_senegal_knowledge(path: Path | None = None) -> dict:
    path = path or Path(__file__).resolve().parents[1] / "data" / "senegal_knowledge.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}
        for region in data.get("regions", []):
            if isinstance(region, dict):
                region["_search_haystack"] = " ".join([
                    str(region.get("name", "")),
                    *map(str, region.get("places", [])),
                    *map(str, region.get("highlights", [])),
                    *map(str, region.get("themes", [])),
                    *map(str, region.get("foods", [])),
                ]).casefold()
        for place in data.get("places", []):
            if isinstance(place, dict):
                place["_search_haystack"] = " ".join([
                    str(place.get("name", "")), str(place.get("summary", "")),
                    str(place.get("history", "")), str(place.get("culture", "")),
                    str(place.get("what_to_see", "")),
                ]).casefold()
        return data
    except (OSError, json.JSONDecodeError):
        return {}

def _knowledge_domain(query: str) -> str:
    value = str(query or "").casefold()
    domain_terms = {
        "travel": ("voyage", "visiter", "séjour", "itinéraire", "plage", "hôtel"),
        "food": ("restaurant", "manger", "cuisine", "plat", "yassa", "thiéboudienne", "mafé"),
        "culture": ("culture", "histoire", "patrimoine", "musée", "musique", "tradition"),
        "transport": ("transport", "ter", "brt", "taxi", "bus", "aéroport"),
        "administration": ("visa", "passeport", "démarche", "document", "consulat"),
        "environment": ("parc", "faune", "mangrove", "environnement", "climat", "biodiversité"),
        "business": ("business", "entreprise", "commerce", "entrepreneur", "entreprendre", "clients", "vente", "projet"),
        "employment": ("emploi", "recrutement", "embauche", "carrière", "métier", "cv", "travail"),
        "education": ("formation", "éducation", "école", "université", "étudier", "apprendre", "cours"),
        "diaspora": ("diaspora", "retour", "transfert", "sénégal-france"),
        "economy": ("prix", "économie", "salaire", "revenus", "investir", "financement"),
    }
    for domain, terms in domain_terms.items():
        if any(term in value for term in terms):
            return domain
    return "general"

_KNOWLEDGE_CONTEXT_CACHE: dict[tuple[int, int, str, int, int], str] = {}
_KNOWLEDGE_CONTEXT_CACHE_MAX = 128


def _knowledge_cache_get(key: tuple[int, int, str, int, int]) -> str | None:
    return _KNOWLEDGE_CONTEXT_CACHE.get(key)


def _knowledge_cache_store(key: tuple[int, int, str, int, int], value: str) -> None:
    if len(_KNOWLEDGE_CONTEXT_CACHE) >= _KNOWLEDGE_CONTEXT_CACHE_MAX and key not in _KNOWLEDGE_CONTEXT_CACHE:
        _KNOWLEDGE_CONTEXT_CACHE.pop(next(iter(_KNOWLEDGE_CONTEXT_CACHE)), None)
    _KNOWLEDGE_CONTEXT_CACHE[key] = value


def format_senegal_knowledge(data, query: str = "", people: list[dict] | None = None, max_regions: int = 5, max_places: int = 8) -> str:
    """Build a compact, query-focused context from structured Senegal knowledge."""
    value = str(query or "").casefold()
    cache_key = (id(data), id(people), value, max_regions, max_places)
    cached = _knowledge_cache_get(cache_key)
    if cached is not None:
        return cached
    lines = [
        "BASE DE CONNAISSANCES NATIONALE DU SÉNÉGAL (référence interne, structurée) :",
        "Utilise ces données comme contexte factuel. Pour les informations actuelles, vérifie le web. Ne transforme pas une déduction en certitude.",
    ]

    profile = data.get("country_profile", {})
    if profile:
        currency = profile.get("currency", {})
        lines.append(
            f"- Repères nationaux : capitale {profile.get('capital')}; monnaie {currency.get('name')} ({currency.get('code')}); "
            f"langue officielle {profile.get('official_language')}; fuseau {profile.get('time_zone')}."
        )

    regions = data.get("regions", [])
    tokens = [token for token in value.split() if len(token) >= 4]
    matched_regions = []
    for region in regions:
        haystack = region.get("_search_haystack", "")
        if tokens and any(token in haystack for token in tokens):
            matched_regions.append(region)
    if matched_regions:
        lines.append("CONTEXTE RÉGIONAL PERTINENT :")
        for region in matched_regions[:max_regions]:
            dossier = region.get("regional_dossier", {})
            foods = region.get("foods") or dossier.get("foods") or []
            highlights = region.get("highlights") or dossier.get("key_places") or []
            lines.append(
                f"- {region.get('name')}: {dossier.get('identity') or ''} "
                f"Localités: {', '.join(region.get('places', [])[:max_places])}. "
                f"À voir: {', '.join(highlights[:max_places])}. "
                f"Spécialités: {', '.join(foods[:6])}. "
                f"Pratique: {dossier.get('practical') or ''}"
            )

    places = data.get("places", [])
    if tokens and places:
        matched_places = []
        for place in places:
            haystack = place.get("_search_haystack", "")
            if any(token in haystack for token in tokens):
                matched_places.append(place)
        if matched_places:
            lines.append("LIEUX PERTINENTS :")
            for place in matched_places[:max_places]:
                lines.append(
                    f"- {place.get('name')}: {place.get('summary', '')} "
                    f"À voir : {place.get('what_to_see', '')}."
                )

    unesco = data.get("unesco_world_heritage", [])
    if unesco and any(token in value for token in ("unesco", "patrimoine", "goree", "gorée", "djoudj", "niokolo", "saloum", "bassari", "mégalith")):
        lines.append("PATRIMOINE MONDIAL UNESCO : " + ", ".join(unesco) + ".")

    if people and tokens:
        matched_people = []
        for person in people:
            haystack = f"{person.get('name', '')} {person.get('period', '')} {person.get('text', '')}".casefold()
            if any(token in haystack for token in tokens):
                matched_people.append(person)
        if matched_people:
            lines.append("PERSONNALITÉS PERTINENTES :")
            for person in matched_people[:4]:
                lines.append(f"- {person.get('name')} ({person.get('period', '')}) : {person.get('text', '')}")

    domain = _knowledge_domain(query)
    modules = data.get("knowledge_modules", {})
    module_key = {
        "travel": "tourism_heritage",
        "culture": "culture_languages_history",
        "food": "food_daily_life",
        "transport": "mobility_travel",
        "administration": "administration_formalities",
        "environment": "environment_agriculture",
        "economy": "economy_society",
        "business": "economy_society",
        "employment": "economy_society",
        "diaspora": "economy_society",
    }.get(domain, domain)
    module = modules.get(module_key)
    if isinstance(module, dict):
        description = module.get("description")
        anchors = module.get("anchors") or []
        stable = module.get("stable_knowledge") or []
        if description:
            lines.append(f"DOMAINE PERTINENT ({domain}) : {description}")
        if anchors:
            lines.append("Repères : " + ", ".join(str(item) for item in anchors[:8]) + ".")
        if stable:
            lines.append("Repères stables : " + " ".join(str(item) for item in stable[:3]))

    result = "\n".join(lines)
    _knowledge_cache_store(cache_key, result)
    return result
