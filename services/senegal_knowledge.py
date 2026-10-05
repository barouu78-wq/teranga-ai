"""Senegal-first knowledge and retrieval policy for Teranga AI.

This module does not pretend to be a static encyclopedia. It gives the response
engine a structured map of Senegal topics and source priorities so it can decide
when fresh web evidence is required.
"""
from __future__ import annotations

import json
import re
import unicodedata
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


_QUERY_STOPWORDS = frozenset({
    "raconte", "racontes", "histoire", "visiter", "visite", "quartier", "quartiers", "comment", "quelle", "quelles",
    "quels", "quel", "pourquoi", "parle", "parler", "dans", "pour", "avec", "faire", "voir", "montre", "photos",
    "photo", "guide", "senegal", "tell", "about", "what", "where", "history", "visit", "show", "connais",
})


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

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
    "health": ("santé", "vaccination", "hôpital", "pharmacie", "urgence", "SAMU", "maladie"),
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
    "prices", "events", "news", "flights", "health",
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

def knowledge_metadata(domain: str, *, dynamic: bool | None = None) -> dict[str, object]:
    """Expose provenance policy alongside structured knowledge."""
    is_dynamic = domain in DYNAMIC_DOMAINS if dynamic is None else bool(dynamic)
    return {
        "domain": domain or "general",
        "source_priority": source_domains(domain),
        "freshness": "fresh_required" if is_dynamic else "stable",
        "confidence": "high" if source_domains(domain) else "medium",
        "requires_web_verification": is_dynamic,
    }


def source_domains(domain: str) -> tuple[str, ...]:
    if domain in {"society", "economy", "agriculture", "territory", "business", "employment", "education"}:
        return SOURCE_PRIORITY
    if domain == "health":
        return ("sante.gouv.sn", "who.int", "samusocial.sn")
    if domain in {"travel", "culture", "environment"}:
        return ("tourisme.gouv.sn", "ansd.sn", "unesco.org", "gov.sn")
    if domain == "administration":
        return ("diplomatie.gouv.sn", "interieur.gouv.sn", "gov.sn")
    if domain == "weather":
        return ("anacim.sn", "ansd.sn", "gov.sn")
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
                region["_search_haystack"] = _fold(" ".join([
                    str(region.get("name", "")),
                    *map(str, region.get("places", [])),
                    *map(str, region.get("highlights", [])),
                    *map(str, region.get("themes", [])),
                    *map(str, region.get("foods", [])),
                ]))
        for place in data.get("places", []):
            if isinstance(place, dict):
                place["_search_haystack"] = _fold(" ".join([
                    str(place.get("name", "")), str(place.get("summary", "")),
                    str(place.get("history", "")), str(place.get("culture", "")),
                    str(place.get("what_to_see", "")),
                ]))
        for dossier in data.get("history_dossiers", []):
            if isinstance(dossier, dict):
                triggers = sorted({_fold(t).strip() for t in dossier.get("triggers", []) if _fold(t).strip()}, key=len, reverse=True)
                dossier["_match"] = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(t) for t in triggers) + r")(?![a-z0-9])") if triggers else None
        for dish in data.get("dishes", []):
            if isinstance(dish, dict):
                names = [str(dish.get("name", "")), *map(str, dish.get("aliases", []))]
                folded = sorted({_fold(name).strip() for name in names if _fold(name).strip()}, key=len, reverse=True)
                dish["_match"] = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(name) for name in folded) + r")(?![a-z0-9])") if folded else None
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def _matched_dishes(data: dict, folded_query: str, limit: int = 4) -> list[dict]:
    """Plats et boissons cités dans la question (nom ou variante d'écriture)."""
    found = []
    for dish in data.get("dishes", []):
        pattern = dish.get("_match") if isinstance(dish, dict) else None
        if pattern is not None and pattern.search(folded_query):
            found.append(dish)
    return found[:limit]


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
        "health": ("santé", "vaccination", "hôpital", "pharmacie", "urgence", "samu", "maladie"),
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
    domain = _knowledge_domain(query)
    metadata = knowledge_metadata(domain)
    lines = [
        "BASE DE CONNAISSANCES NATIONALE DU SÉNÉGAL (référence interne, structurée) :",
        f"Provenance: priorité {', '.join(metadata['source_priority'][:4]) or 'interne'}; fraîcheur={metadata['freshness']}; confiance={metadata['confidence']}.",
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
    # Sans accents ni apostrophes (« Gorée » = « goree », « l'histoire » =
    # « histoire ») ; les mots de la question qui ne désignent pas un lieu
    # (raconte, histoire, visiter…) ne servent pas à choisir les lieux.
    tokens = [token for token in re.findall(r"[a-z0-9]+", _fold(value)) if len(token) >= 4 and token not in _QUERY_STOPWORDS]
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
        # Classement par pertinence : un mot présent dans le nom du lieu compte
        # triple (« fort de Sédhiou », « marché de Diaobé ») ; sinon l'ordre du
        # fichier faisait passer Gorée ou Mbour avant le lieu demandé.
        scored = []
        for index, place in enumerate(places):
            haystack = place.get("_search_haystack", "")
            name = _fold(place.get("name", ""))
            hits = sum(1 for token in tokens if token in haystack)
            if hits:
                score = hits + 2 * sum(1 for token in tokens if token in name)
                scored.append((-score, index, place))
        matched_places = [place for _, _, place in sorted(scored, key=lambda item: item[:2])]
        if matched_places:
            lines.append("LIEUX PERTINENTS :")
            for rank, place in enumerate(matched_places[:max_places]):
                # Histoire détaillée pour les 3 lieux les plus pertinents : de
                # quoi raconter comme un guide sans alourdir le contexte.
                history = f" Histoire : {place.get('history')}" if rank < 3 and place.get("history") else ""
                lines.append(
                    f"- {place.get('name')}: {place.get('summary', '')} "
                    f"À voir : {place.get('what_to_see', '')}.{history}"
                )

    unesco = data.get("unesco_world_heritage", [])
    if unesco and any(token in value for token in ("unesco", "patrimoine", "goree", "gorée", "djoudj", "niokolo", "saloum", "bassari", "mégalith")):
        lines.append("PATRIMOINE MONDIAL UNESCO : " + ", ".join(unesco) + ".")

    if people and tokens:
        # Une personne citée par son nom passe avant les mentions dans un texte ;
        # le nom est comparé mot à mot (« Laye » ne désigne pas « Abdoulaye »).
        named, mentioned = [], []
        for person in people:
            name_words = set(re.findall(r"[a-z0-9]+", _fold(person.get("name", ""))))
            haystack = _fold(f"{person.get('name', '')} {person.get('period', '')} {person.get('text', '')}")
            name_hits = sum(1 for token in tokens if token in name_words)
            if name_hits:
                named.append((-name_hits, len(named), person))
            elif any(token in haystack for token in tokens):
                mentioned.append(person)
        matched_people = [person for _, _, person in sorted(named, key=lambda item: item[:2])] or mentioned
        if matched_people:
            lines.append("PERSONNALITÉS PERTINENTES :")
            for person in matched_people[:4]:
                lines.append(f"- {person.get('name')} ({person.get('period', '')}) : {person.get('text', '')}")

    folded_query = _fold(value)
    dishes = _matched_dishes(data, folded_query)
    if dishes:
        lines.append("PLATS ET BOISSONS PERTINENTS :")
        for dish in dishes:
            where = f" Où : {dish.get('where')}." if dish.get("where") else ""
            lines.append(f"- {dish.get('name')} ({dish.get('kind')}) : {dish.get('text')}{where}")

    for dossier in data.get("history_dossiers", []):
        pattern = dossier.get("_match") if isinstance(dossier, dict) else None
        if pattern is not None and pattern.search(folded_query):
            lines.append(f"DOSSIER HISTORIQUE — {dossier.get('title')} :")
            lines.extend(f"- {section}" for section in dossier.get("sections", []))

    phrases = data.get("wolof_phrases") or []
    if phrases and re.search(r"(?<![a-z])wolof(?![a-z])", folded_query):
        lines.append("PHRASES WOLOF SÛRES (orthographe officielle ; à réutiliser telles quelles, sans en inventer d'autres) :")
        lines.append("; ".join(f"{item.get('wo')} = {item.get('fr')}" for item in phrases) + ".")

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
        "education": "education_sports_events",
        "health": "health_safety",
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
