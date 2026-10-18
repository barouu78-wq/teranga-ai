"""Senegal-first knowledge and retrieval policy for Teranga AI.

This module does not pretend to be a static encyclopedia. It gives the response
engine a structured map of Senegal topics and source priorities so it can decide
when fresh web evidence is required.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

# Official administrative coverage: all 14 regions of Senegal.
SENEGAL_REGIONS = (
    "Dakar", "Diourbel", "Fatick", "Kaffrine", "Kaolack", "Kédougou", "Kolda",
    "Louga", "Matam", "Saint-Louis", "Sédhiou", "Tambacounda", "Thiès", "Ziguinchor",
)

# Noms wolof de Dakar, tels que les écrivent les suggestions wolof du site (static/home.js) :
# « Lan mooy tàkk-tàkk Dakaar tey? », « Nettali ma taariixu Ndakaaru… ».
WOLOF_PLACE_NAMES = {"dakaar": "dakar", "ndakaaru": "dakar"}

REGION_ALIASES = {
    "Dakar": ("dakar", *WOLOF_PLACE_NAMES), "Diourbel": ("diourbel",), "Fatick": ("fatick",),
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
    # Mots courants des questions pratiques : ils ne désignent jamais un lieu
    # (« combien vaut 100 euros » faisait remonter le Niokolo-Koba, « vaut le détour »).
    "combien", "vaut", "valent", "quand", "faut", "sont", "etre", "bien", "quoi", "cette", "entre", "avoir",
    "acheter", "payer", "prix", "cout", "coute", "coutent", "euros", "euro", "dollars", "dollar", "fcfa",
    "francs", "franc", "when", "which", "much", "many", "does", "from", "with", "have", "there", "best",
    "good", "need", "should", "your", "enfant", "jour", "jours", "date", "dates", "numero", "numeros",
    "appeler", "besoin", "doit", "dois", "peut", "peux", "possible", "meilleur", "meilleure", "sénégal",
    # Mots de liaison, verbes et adjectifs courants : « depuis hier » ou « où se trouve » faisaient remonter Gorée ou
    # le parc du Niokolo-Koba (qui emploient ces mots), « visite guidée » tous les lieux qui parlent d'un guide,
    # « souvenirs » la Cathédrale du Souvenir africain, « sénégalais » les manufactures sénégalaises.
    "depuis", "pendant", "aller", "allez", "allons", "venir", "viens", "vient", "pays", "moment", "trouve", "trouver",
    "trouvent", "cherche", "chercher", "cherchez", "longue", "famille", "frais", "naissance", "arrivee", "voyage",
    "voyages", "voyager", "beaucoup", "fils", "taxi", "taxis", "senegalais", "senegalaise", "senegalaises",
    "francais", "francaise", "francaises", "guidee", "guidees", "guides", "souvenir", "souvenirs",
    "femme", "femmes", "homme", "hommes", "seul", "seule",
    # Villes et pays où vit la diaspora : ils ne désignent pas un lieu du Sénégal (« passeport à Paris »).
    "paris", "france", "europe", "usa", "canada", "belgique", "espagne", "italie", "allemagne",
    # Mois : « en décembre » ne désigne ni un lieu ni une personne.
    "janvier", "fevrier", "mars", "avril", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
    # Mots administratifs : « titre de séjour » ou « titre foncier » faisaient venir Sadio Mané et Koli Tenguella
    # (leurs fiches parlent de « titres »), « séjour » la Grande Mosquée de Diourbel.
    "titre", "titres", "sejour", "sejours",
    # « le billet d'avion est trop cher » faisait venir Gorée (billet de chaloupe) et Cap Skirring (accès en avion).
    "billet", "billets", "avion", "avions",
})

# La langue comme sujet (« comment on dit merci en wolof », « apprendre le wolof ») : le mot ne désigne ni un lieu
# ni une personne (il faisait venir Richard-Toll, Louga et Birago Diop). Les phrases wolof sûres restent ajoutées.
_LANGUE_SUJET = re.compile(
    r"\b(?:en|le|du|parler|parle|parles|apprendre|apprends|traduire|traduis|traduction|langue|mots?|phrases?|dit|dire)"
    r"\s+(?:le\s+)?(?:wolof|pulaar|pular|serere?|diola|joola|mandingue)\b"
)

# « Ça ne marche pas » est le verbe : seul « marché » désigne un marché (les accents sont retirés avant la recherche).
_VERBE_MARCHER = re.compile(
    r"\b(?:ca|cela|il|elle|ils|elles|on|je|tu|nous|vous|ne|n|wave|orange money|internet|reseau|wifi|appli|application|"
    r"telephone|compteur|carte)\s+march(?:e|ent|ons|ez)\b|"
    r"\bmarch(?:e|ent)\s+(?:pas|plus|bien|mal|toujours|encore|jamais|aussi)\b"
)


_SHORT_STOPWORDS = frozenset({
    "les", "des", "une", "est", "que", "qui", "the", "and", "for", "how", "sur", "aux", "pas", "mon", "ton", "son",
    "par", "via", "oui", "non", "bon", "ses", "mes", "tes", "nos", "vos", "leur", "car", "donc", "mais", "elle", "ils",
    "nous", "vous", "moi", "toi", "lui", "can", "you", "are", "was", "what", "who", "why", "any", "get", "see", "eat",
    "ici", "peu", "tre", "plus", "tout", "tous", "faut", "fait", "dit", "vas", "vais", "veux", "cest", "quoi", "lequel",
    "naka", "nga", "laa", "dem", "ngi", "bou", "rek", "ana", "ans", "eau", "ete", "jai", "ont", "fin", "mois",
})


# Mots communs d'un nom de lieu (« Village des Arts », « Musée Senghor ») : seuls dans la question, ils ne nomment pas
# ce lieu (« musée » reste un nom : il dit ce qu'est le lieu, et « quels musées visiter » doit ramener les musées). « un village à visiter » ne ramenait plus que le Village des Arts, « où est né Senghor ? » que le musée et
# plus Joal-Fadiouth. Avec un autre mot du nom (« musée Senghor », « Maison des Esclaves »), le lieu reste nommé.
_NOMS_COMMUNS = frozenset({"village", "villages", "maison", "maisons", "senghor", "ndiaye"})


# Une personne n'est retrouvée par un mot de sa fiche (et non par son nom) que si au plus trois fiches l'emploient.
_PEOPLE_MAX_FICHES = 3


def _words(text: str) -> frozenset:
    return frozenset(re.findall(r"[a-z0-9]+", text))


def _hit(token: str, words: frozenset) -> bool:
    """Le mot de la question désigne-t-il ce lieu ? Mot entier, ou pluriel/forme longue
    (« plages » ↔ « plage ») à partir de 5 lettres, jamais un bout de mot (« vaut » ≠ « vautour »)."""
    if token in words:
        return True
    if len(token) < 5:
        return False
    # Seulement les variations de fin de mot (pluriel, féminin : 2 lettres au plus) :
    # « sénégalaise » ne doit pas désigner tous les lieux qui citent « Sénégal ».
    return any(
        (w.startswith(token) and len(w) - len(token) <= 2)
        or (len(w) >= 5 and token.startswith(w) and len(token) - len(w) <= 2)
        for w in words
    )


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
    # Ferry et chaloupe : sans eux, « prix du ferry pour Ziguinchor » tombait dans « economy » (mot « prix »).
    "transport": ("transport", "TER", "BRT", "bus", "taxi", "aéroport", "AIBD", "ferry", "ferries", "chaloupe"),
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

def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _contains_domain_term(value: str, term: str) -> bool:
    """Mot entier, sans tenir compte des accents ni du pluriel simple.

    « hopital » trouve « hôpital », « plages » trouve « plage », mais « teranga »
    ne trouve pas « ter » et « plateau » ne trouve pas « plat ».
    """
    normalized = _fold(term).strip()
    if not normalized:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized) + r"(?:s|x)?(?!\w)"
    return bool(re.search(pattern, _fold(value)))


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
                region["_search_words"] = _words(region["_search_haystack"])
                # Où se trouve la région (nom, localités, sites) : sans les thèmes ni les spécialités, que
                # beaucoup de régions partagent (« poisson », « thiéboudienne »).
                region["_geo_words"] = _words(_fold(" ".join([
                    str(region.get("name", "")),
                    *map(str, region.get("places", [])),
                    *map(str, region.get("highlights", [])),
                ])))
        for place in data.get("places", []):
            if isinstance(place, dict):
                place["_search_haystack"] = _fold(" ".join([
                    str(place.get("name", "")), str(place.get("summary", "")),
                    str(place.get("history", "")), str(place.get("culture", "")),
                    str(place.get("what_to_see", "")), str(place.get("access", "")),
                    *map(str, place.get("aliases", []) or []),
                ]))
                # Nom et autres noms (« Pink Lake », « Goree Island ») : un mot
                # trouvé ici compte davantage dans le classement.
                place["_search_names"] = _fold(" ".join([str(place.get("name", "")), *map(str, place.get("aliases", []) or [])]))
                place["_search_words"] = _words(place["_search_haystack"])
                place["_search_name_words"] = _words(place["_search_names"])
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


# Langues dont la base a des phrases sûres (voir format_senegal_knowledge) : une question sur elles a son propre sujet.
_LANGUAGE_SUBJECT = re.compile(r"(?<![a-z])(?:wolof|pulaar|pular|fulfulde)(?![a-z])")


def _place_names_pattern(data: dict) -> re.Pattern | None:
    """Noms et autres noms des lieux de la base, en expressions entières (« lac rose », « djoudj », « sandaga »).

    Calculé une fois, puis gardé dans la base elle-même (comme les autres clés « _ »)."""
    if "_place_names_match" not in data:
        names = set()
        for place in data.get("places", []):
            if isinstance(place, dict):
                for name in (place.get("name", ""), *(place.get("aliases") or [])):
                    folded = _fold(name).strip()
                    if len(folded) >= 3:
                        names.add(folded)
        ordered = sorted(names, key=len, reverse=True)
        data["_place_names_match"] = (
            re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(n) for n in ordered) + r")(?![a-z0-9])") if ordered else None
        )
    return data["_place_names_match"]


def names_own_subject(data, message: str) -> bool:
    """Le message nomme-t-il, seul, un sujet de la base : lieu, plat ou boisson, dossier historique, langue ?

    Sert à reconnaître un changement de sujet (services/intelligence.py, `starts_new_subject`) : les fiches du
    fil ne sont alors plus ajoutées à celles de la question."""
    if not isinstance(data, dict):
        return False
    folded = _fold(message)
    if _LANGUAGE_SUBJECT.search(folded):
        return True
    if _matched_dishes(data, folded, limit=1):
        return True
    if any(isinstance(d, dict) and d.get("_match") is not None and d["_match"].search(folded) for d in data.get("history_dossiers", [])):
        return True
    pattern = _place_names_pattern(data)
    return bool(pattern and pattern.search(folded))


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
        if any(_contains_domain_term(value, term) for term in terms):
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

        folded_value = _fold(value)
        if re.search(r"urgence|police|pompier|samu|ambulance|secours|accident|hopital|malade|(?<![a-z])vol(?:e|ee|es|ees|er|eur|eurs)(?![a-z])", folded_value):
            numbers = "; ".join(f"{n.get('service')} {n.get('number')} ({n.get('scope')})" for n in profile.get("emergency_numbers", []))
            if numbers:
                lines.append(f"- Numéros d'urgence au Sénégal : {numbers}.")
        if re.search(r"superficie|frontiere|voisin|independance|combien de region|departement|langue|population|fleuve|geographie|indicatif|(?<![a-z])prises?(?![a-z])(?! (?:de(?! courant)|d|en|a)\b)|electri|voltage|conduite|conduit", folded_value):
            geo = profile.get("geography", {})
            practical = profile.get("practical", {})
            lines.append(
                f"- Profil : superficie {profile.get('area_km2')} km² ; {profile.get('administrative_regions')} régions, "
                f"{profile.get('departments')} départements ; indépendance le {profile.get('independence_date')} ; "
                f"langues courantes {', '.join(profile.get('common_languages', []))} ; pays voisins {', '.join(geo.get('neighboring_countries', []))} ; "
                f"fleuves {', '.join(geo.get('major_rivers', []))} ; indicatif téléphonique {practical.get('phone_code')} ; "
                f"électricité {practical.get('electricity')} ; conduite {practical.get('driving_side')}. Population : chiffre à vérifier auprès de l'ANSD."
            )

    regions = data.get("regions", [])
    # Sans accents ni apostrophes (« Gorée » = « goree », « l'histoire » =
    # « histoire ») ; les mots de la question qui ne désignent pas un lieu
    # (raconte, histoire, visiter…) ne servent pas à choisir les lieux.
    # Mots de 3 lettres gardés (« HLM », « lac », « TER ») sauf les mots outils.
    # Un nom wolof (« Ndakaaru ») cherche les mêmes lieux que son nom français.
    tokens = [
        WOLOF_PLACE_NAMES.get(token, token)
        for token in re.findall(r"[a-z0-9]+", _LANGUE_SUJET.sub(" ", _VERBE_MARCHER.sub(" ", _fold(value))))
        if len(token) >= 3 and token not in _QUERY_STOPWORDS and token not in _SHORT_STOPWORDS and not token.isdigit()
    ]
    places = data.get("places", [])
    ranked = []
    # Mots de la question qui nomment le lieu le plus pertinent, quand il est nommé par au moins deux d'entre eux
    # (« lac » et « rose ») : un lieu ou une région qui ne partage qu'une partie de ce nom (« lac » pour le lac de
    # Guiers et la région de Saint-Louis) n'est pas demandé.
    named_tokens: set = set()
    if tokens and places:
        # Classement par pertinence : un mot présent dans le nom du lieu compte
        # triple (« fort de Sédhiou », « marché de Diaobé ») ; sinon l'ordre du
        # fichier faisait passer Gorée ou Mbour avant le lieu demandé.
        scored = []
        for index, place in enumerate(places):
            words = place.get("_search_words") or _words(place.get("_search_haystack", ""))
            name_words = place.get("_search_name_words") or _words(_fold(place.get("name", "")))
            hit_tokens = {token for token in tokens if _hit(token, words)}
            if hit_tokens:
                name_tokens = {token for token in tokens if _hit(token, name_words)}
                if len(name_tokens) == 1 and name_tokens <= _NOMS_COMMUNS:
                    name_tokens = set()
                score = len([token for token in tokens if token in hit_tokens]) + 2 * len([t for t in tokens if t in name_tokens])
                scored.append((-score, index, place, frozenset(hit_tokens), frozenset(name_tokens)))
        ranked = sorted(scored, key=lambda item: item[:2])
        # Quand un lieu est nommé dans la question (score 3 ou plus), un lieu qui ne partage avec elle qu'un seul mot
        # de son texte (score 1) n'est pas demandé : « Saly » ne ramène pas Ziguinchor parce qu'il y fait « nuit ».
        if ranked and -ranked[0][0] >= 3:
            ranked = [item for item in ranked if -item[0] >= 2]
        if ranked and len(ranked[0][4]) >= 2:
            named_tokens = set(ranked[0][4])
            ranked = [ranked[0]] + [
                item for item in ranked[1:]
                if not (item[4] and item[4] < named_tokens and item[3] <= named_tokens)
            ]

    matched_regions = []
    for region in regions:
        words = region.get("_search_words") or _words(region.get("_search_haystack", ""))
        if tokens and any(_hit(token, words) for token in tokens):
            matched_regions.append(region)
    # Une région nommée (ou dont on cite une localité) passe avant celles qui ne ressemblent à la question que par
    # un thème ou un plat : « poisson à Saint-Louis » ne ramène pas quatre autres régions.
    located = [
        region for region in matched_regions
        if any(_hit(token, region.get("_geo_words") or frozenset()) for token in tokens)
    ]
    matched_regions = located or matched_regions
    # Un lieu nommé dans la question, mais qu'aucune région ne cite : les régions qui ne lui ressemblent que par un
    # thème ou un plat (« poisson ») ne sont pas demandées (« une marchande de poisson à Soumbédioune » en
    # recevait cinq).
    if not located and ranked and ranked[0][4]:
        matched_regions = []
    if named_tokens:
        matched_regions = [
            region for region in matched_regions
            if all(_hit(token, region.get("_search_words") or frozenset()) for token in named_tokens)
            or any(_hit(token, region.get("_search_words") or frozenset()) for token in tokens if token not in named_tokens)
        ]
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

    if ranked:
        matched_places = [item[2] for item in ranked]
        if matched_places:
            lines.append("LIEUX PERTINENTS :")
            for rank, place in enumerate(matched_places[:max_places]):
                # Histoire détaillée pour les 3 lieux les plus pertinents : de
                # quoi raconter comme un guide sans alourdir le contexte.
                history = f" Histoire : {place.get('history')}" if rank < 3 and place.get("history") else ""
                access = f" Accès : {place.get('access')}" if rank < 3 and place.get("access") else ""
                lines.append(
                    f"- {place.get('name')}: {place.get('summary', '')} "
                    f"À voir : {place.get('what_to_see', '')}.{history}{access}"
                )

    unesco = data.get("unesco_world_heritage", [])
    if unesco and any(token in value for token in ("unesco", "patrimoine", "goree", "gorée", "djoudj", "niokolo", "saloum", "bassari", "mégalith")):
        lines.append("PATRIMOINE MONDIAL UNESCO : " + ", ".join(unesco) + ".")

    if people and tokens:
        # Une personne citée par son nom passe avant les mentions dans un texte ;
        # le nom est comparé mot à mot (« Laye » ne désigne pas « Abdoulaye »).
        named, mentioned = [], []
        fiches = []
        for person in people:
            name_words = set(re.findall(r"[a-z0-9]+", _fold(person.get("name", ""))))
            # La fiche s'arrête au premier saut de ligne : la suite d'une entrée peut être une consigne de style,
            # qui ne dit rien de la personne et ne doit pas servir à la retrouver.
            fiche = str(person.get("text", "")).split("\n", 1)[0]
            fiches.append((person, name_words, _words(_fold(f"{person.get('name', '')} {person.get('period', '')} {fiche}"))))
        # Un mot que plus de _PEOPLE_MAX_FICHES fiches emploient (« dakar », « politique ») ne désigne personne.
        usage = Counter(word for _, _, words in fiches for word in words)
        for person, name_words, words in fiches:
            name_hits = sum(1 for token in tokens if token in name_words)
            if name_hits:
                named.append((-name_hits, len(named), person))
                continue
            # Mots entiers (« cher » n'est pas dans « chercheur »), rares, d'au moins 5 lettres (« TER », « BRT »,
            # « près » sont trop ambigus).
            rare_hits = sum(1 for token in tokens if len(token) >= 5 and token in words and usage[token] <= _PEOPLE_MAX_FICHES)
            if rare_hits:
                mentioned.append((-rare_hits, len(mentioned), person))
        matched_people = [person for _, _, person in sorted(named, key=lambda item: item[:2])] or [
            person for _, _, person in sorted(mentioned, key=lambda item: item[:2])
        ]
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

    pulaar = data.get("pulaar_phrases") or []
    if pulaar and re.search(r"(?<![a-z])(pulaar|pular|peule?s?|peulh|haalpulaar|halpulaar|fouta|fuuta|futa|fulfulde)(?![a-z])", folded_query):
        lines.append("PHRASES PULAAR SÛRES (à réutiliser telles quelles, sans en inventer d'autres) :")
        lines.append("; ".join(f"{item.get('pu')} = {item.get('fr')}" for item in pulaar) + ".")

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
