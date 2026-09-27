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

def load_senegal_knowledge(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

def format_senegal_knowledge(data):
    profile = data.get("country_profile", {})
    regions = data.get("regions", [])
    lines = [
        "BASE DE CONNAISSANCES NATIONALE DU SÉNÉGAL (référence interne, multisources) :",
        "Ne pas réduire cette base à l'UNESCO : elle couvre territoire, vie quotidienne, météo/climat, santé, mobilité, formalités, économie, culture, histoire, gastronomie, environnement et tourisme.",
    ]
    modules = data.get("knowledge_modules", {})
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
