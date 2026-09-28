"""Senegal-first knowledge and retrieval policy for Teranga AI.

This module does not pretend to be a static encyclopedia. It gives the response
engine a structured map of Senegal topics and source priorities so it can decide
when fresh web evidence is required.
"""
from __future__ import annotations

import json
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
    "economy": ("économie", "emploi", "prix", "entreprise", "commerce", "PIB"),
    "society": ("population", "éducation", "santé", "emploi", "démographie"),
    "environment": ("environnement", "parc", "faune", "forêt", "climat"),
    "diaspora": ("diaspora", "Sénégal-France", "retour", "transfert"),
    "administration": ("démarche", "document", "visa", "administration", "consulat"),
}

DYNAMIC_DOMAINS = {
    "weather", "transport", "restaurant", "travel", "administration",
    "prices", "events", "news", "flights",
}

def classify_domain(text: str) -> str:
    value = str(text or "").lower()
    if any(term in value for term in ("météo", "meteo", "weather", "pluie", "température", "temperature")):
        return "weather"
    for domain, terms in SENEGAL_DOMAINS.items():
        if any(term.lower() in value for term in terms):
            return domain
    return "general"

def needs_fresh_web(domain: str, text: str) -> bool:
    value = str(text or "").lower()
    return domain in DYNAMIC_DOMAINS or any(
        marker in value for marker in ("aujourd", "maintenant", "actuel", "latest",
                                       "cette semaine", "prix", "ouvert", "horaires")
    )

def source_domains(domain: str) -> tuple[str, ...]:
    if domain in {"society", "economy", "agriculture", "territory"}:
        return SOURCE_PRIORITY
    if domain in {"travel", "culture", "environment"}:
        return ("tourisme.gouv.sn", "ansd.sn", "unesco.org", "gov.sn")
    if domain == "administration":
        return ("diplomatie.gouv.sn", "interieur.gouv.sn", "gov.sn")
    if domain == "weather":
        return ("meteofrance.com", "ansd.sn", "gov.sn")
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
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

def format_senegal_knowledge(data, query: str = "", people: list[dict] | None = None, max_regions: int = 5, max_places: int = 8) -> str:
    """Build a compact, query-focused context from structured Senegal knowledge."""
    value = str(query or "").casefold()
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
        haystack = " ".join([
            str(region.get("name", "")),
            *map(str, region.get("places", [])),
            *map(str, region.get("highlights", [])),
            *map(str, region.get("themes", [])),
            *map(str, region.get("foods", [])),
        ]).casefold()
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
            haystack = " ".join([
                str(place.get("name", "")), str(place.get("summary", "")),
                str(place.get("history", "")), str(place.get("culture", "")),
                str(place.get("what_to_see", "")),
            ]).casefold()
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

    scope = data.get("knowledge_scope", {}).get("domains", {})
    if scope and not tokens:
        lines.append("DOMAINES COUVERTS : " + ", ".join(scope.keys()) + ".")
    dynamic_topics = data.get("dynamic_topics", [])
    if dynamic_topics:
        lines.append("SUJETS À VÉRIFIER EN TEMPS RÉEL : " + ", ".join(dynamic_topics) + ".")
    return "\n".join(lines)
