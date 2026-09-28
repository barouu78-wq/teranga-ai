"""Senegal-first knowledge and retrieval policy for Teranga AI.

This module does not pretend to be a static encyclopedia. It gives the response
engine a structured map of Senegal topics and source priorities so it can decide
when fresh web evidence is required.
"""
from __future__ import annotations

import json
from pathlib import Path

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

def format_senegal_knowledge(data, query: str = "", people: list[dict] | None = None, max_regions: int = 3, max_places: int = 8):
    profile = data.get("country_profile", {})
    regions = data.get("regions", [])
    lines = [
        "BASE DE CONNAISSANCES NATIONALE DU SÉNÉGAL (référence interne, multisources) :",
        "Ne pas réduire cette base à l'UNESCO : elle couvre territoire, vie quotidienne, météo/climat, santé, mobilité, formalités, économie, culture, histoire, gastronomie, environnement et tourisme.",
    ]
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
        geography = profile.get("geography", {})
        if geography:
            lines.append(
                f"- Géographie : voisins {', '.join(geography.get('neighboring_countries', []))}; "
                f"fleuves {', '.join(geography.get('major_rivers', []))}; zones {', '.join(geography.get('major_geographic_areas', []))}."
            )

    regions = data.get("regions", [])
    matched_regions = []
    if value:
        for region in regions:
            haystack = " ".join([
                str(region.get("name", "")),
                *map(str, region.get("places", [])),
                *map(str, region.get("highlights", [])),
                *map(str, region.get("themes", [])),
                *map(str, region.get("foods", [])),
            ]).casefold()
            if any(token and token in haystack for token in value.split() if len(token) > 2):
                matched_regions.append(region)
    selected_regions = matched_regions[:max_regions] if matched_regions else regions[:0]
    if selected_regions:
        lines.append("CONTEXTE RÉGIONAL PERTINENT :")
        for region in selected_regions:
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
    if value and places:
        matched_places = []
        for place in places:
            haystack = " ".join([
                str(place.get("name", "")), str(place.get("summary", "")),
                str(place.get("history", "")), str(place.get("culture", "")),
                str(place.get("what_to_see", "")),
            ]).casefold()
            if any(token and token in haystack for token in value.split() if len(token) > 2):
                matched_places.append(place)
        if matched_places:
            lines.append("LIEUX PERTINENTS :")
            for place in matched_places[:max_places]:
                lines.append(
                    f"- {place.get('name')}: {place.get('summary', '')} "
                    f"À voir : {place.get('what_to_see', '')}."
                )

    unesco = data.get("unesco_world_heritage", [])
    if unesco and any(token in value for token in ("unesco", "patrimoine", "goree", "gorée", "saint-louis", "djoudj", "niokolo", "saloum", "bassari", "mégalith")):
        lines.append("PATRIMOINE MONDIAL UNESCO : " + ", ".join(unesco) + ".")

    if people and value:
        matched_people = []
        for person in people:
            haystack = f"{person.get('name', '')} {person.get('period', '')} {person.get('text', '')}".casefold()
            if any(token and token in haystack for token in value.split() if len(token) > 2):
                matched_people.append(person)
        if matched_people:
            lines.append("PERSONNALITÉS PERTINENTES :")
            for person in matched_people[:4]:
                lines.append(f"- {person.get('name')} ({person.get('period', '')}) : {person.get('text', '')}")

    scope = data.get("knowledge_scope", {}).get("domains", {})
    if scope and not value:
        lines.append("DOMAINES COUVERTS : " + ", ".join(scope.keys()) + ".")
    dynamic_topics = data.get("dynamic_topics", [])
    if dynamic_topics:
        lines.append("SUJETS À VÉRIFIER EN TEMPS RÉEL : " + ", ".join(dynamic_topics) + ".")
    sources = data.get("source_registry", [])
    if sources and (not value or any(token in value for token in ("source", "vérifie", "actuel", "statistique"))):
        lines.append("SOURCES DE RÉFÉRENCE : " + "; ".join(f"{s.get('name')}: {s.get('role')}" for s in sources[:10]) + ".")
    reference_date = data.get("current_reference_date")
    if reference_date:
        lines.append(f"DATE DE RÉFÉRENCE DE LA BASE : {reference_date}; elle ne remplace pas une vérification web.")

    if modules:
        lines.append("MODULES NATIONAUX COMPLÉMENTAIRES :")
        for name, module in modules.items():
            description = module.get("description") or ""
            if description:
                lines.append(f"- {name}: {description}")
            for key in ("anchors", "languages", "cultural_areas", "traditions", "important_context", "stable_knowledge", "live_topics", "modes", "key_nodes", "sectors", "regional_examples", "ecosystems", "topics", "food_topics", "daily_topics", "categories", "major_areas"):
                values = module.get(key)
                if values:
                    lines.append(f"  {key}: {', '.join(map(str, values))}")
            rule = module.get("rule")
            if rule:
                lines.append(f"  règle: {rule}")
            source = module.get("live_source")
            if source:
                lines.append(f"  source temps réel: {source}")
    if profile:
        lines.append("REPÈRES NATIONAUX :")
        lines.append(
            f"- Capitale : {profile.get('capital')}; superficie : {profile.get('area_km2')} km²; "
            f"langue officielle : {profile.get('official_language')}; monnaie : {profile.get('currency', {}).get('name')} ({profile.get('currency', {}).get('code')}); "
            f"fuseau : {profile.get('time_zone')}; indépendance : {profile.get('independence_date')}."
        )
        geography = profile.get("geography", {})
        if geography:
            lines.append(
                f"- Géographie : façade {geography.get('coastline')}; pays voisins : {', '.join(geography.get('neighboring_countries', []))}; "
                f"grands fleuves : {', '.join(geography.get('major_rivers', []))}; zones : {', '.join(geography.get('major_geographic_areas', []))}."
            )
        climate = profile.get("climate", {})
        if climate:
            lines.append(f"- Climat : {climate.get('description')}")
        emergencies = profile.get("emergency_numbers", [])
        if emergencies:
            lines.append("URGENCES : " + "; ".join(f"{x.get('service')} {x.get('number')}" for x in emergencies) + ".")
    for region in regions:
        places = ", ".join(region.get("places", [])[:12])
        highlights = ", ".join(region.get("highlights", [])[:10])
        departments = ", ".join(region.get("departments", [])[:8])
        lines.append(
            f"- {region.get('name')}: départements = {departments}; localités = {places}; "
            f"points d'intérêt = {highlights}."
        )
    places = data.get("places", [])
    if places:
        lines.append("Lieux détaillés :")
        for place in places[:60]:
            what = "; ".join(str(place.get("what_to_see", "")).split(";")[:5])
            lines.append(f"- {place.get('name')}: {place.get('summary', '')} À voir : {what}.")
    domains = data.get("knowledge_scope", {}).get("domains", {})
    if domains:
        lines.append("DOMAINES À COUVRIR :")
        for key, description in domains.items():
            lines.append(f"- {key}: {description}")
    sources = data.get("source_registry", [])
    if sources:
        lines.append("SOURCES DE RÉFÉRENCE :")
        for source in sources:
            lines.append(f"- {source.get('name')}: {source.get('role')}.")
    reference_date = data.get("current_reference_date")
    if reference_date:
        lines.append(f"DATE DE RÉFÉRENCE DE LA BASE : {reference_date}. Cette date ne remplace jamais une vérification web pour une information actuelle.")
    dynamic_topics = data.get("dynamic_topics", [])
    if dynamic_topics:
        lines.append("SUJETS À VÉRIFIER EN TEMPS RÉEL : " + ", ".join(dynamic_topics) + ".")
    unesco = ", ".join(data.get("unesco_world_heritage", []))
    if unesco:
        lines.append(f"Patrimoine mondial UNESCO (une partie du patrimoine, pas toute la connaissance nationale) : {unesco}.")
    return "\n".join(lines)
