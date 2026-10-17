"""Web retrieval policy for Teranga AI V3.1.

Keeps web quality and latency decisions outside the Flask route so they can be
tested without loading the full application.
"""
from __future__ import annotations

import re
from functools import lru_cache

from services.validation import normalize

# Liste FERMÉE de domaines pour l'outil de recherche web (allowed_domains) : rien en dehors n'est lu.
# Seulement pour les sujets où la source officielle EST la réponse (statistiques, démarches, météo).
# Les sites de l'État sénégalais sont en « .gouv.sn » (base : authoritative_sources), d'où « gouv.sn ».
# Ferry, hôtel, restaurant, prix, concert : la réponse est chez l'opérateur, absent de ces listes ;
# ces sujets n'ont donc pas de liste fermée (les sources à privilégier restent écrites dans le prompt).
SOURCE_FILTERS = {
    "society": ("ansd.sn", "gouv.sn", "who.int", "worldbank.org"),
    "agriculture": ("ansd.sn", "agriculture.gouv.sn", "gouv.sn", "fao.org"),
    "territory": ("ansd.sn", "gouv.sn", "tourisme.gouv.sn"),
    "administration": ("diplomatie.gouv.sn", "interieur.gouv.sn", "gouv.sn"),
    "weather": ("anacim.sn", "ansd.sn", "gouv.sn"),
}

@lru_cache(maxsize=32)
def _compiled_term_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = "|".join(
        re.escape(term)
        for term in sorted(set(terms), key=len, reverse=True)
    )
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    if not text or not terms:
        return False
    return bool(_compiled_term_pattern(terms).search(text))


def preferred_domains(domain: str) -> tuple[str, ...]:
    return SOURCE_FILTERS.get(str(domain or ""), ())

def search_context_size(domain: str, planner: bool = False) -> str:
    return "medium" if planner or domain in {"administration", "society", "economy"} else "low"


# Uniquement les sujets vraiment changeants — évite la recherche web sur chaque question.
WEB_HINTS = (
    "photo", "photos", "image", "images", "visuel", "visuels", "montre moi", "montre-moi",
    "a quoi ressemble", "à quoi ressemble", "a quoi ça ressemble", "à quoi ça ressemble",
    "aujourd'hui", "aujourd’hui", "maintenant", "actuel", "actuelle",
    "actuels", "actuelles", "récent", "récente", "récentes",
    "horaire", "horaires", "ouvert", "ouverte",
    "disponible", "disponibilité", "réservation",
    "événement", "evenement", "météo", "meteo", "climat", "température", "temperature", "pluie", "pluies", "orage", "vent", "humidité", "humidite",
    # « now » seul retiré : « ok now tell me about… » ; « right now » reste (marqueurs du moment).
    "actualité", "actualités", "news", "today",
    "current", "latest", "recent", "schedule", "hours",
    "open", "available", "availability", "booking", "weather", "event",
    "visa", "ferry", "cfa", "taux de change", "taux",
    "sim", "orange money", "week-end", "weekend", "ce soir", "demain",
    # « manger » / « eat » seuls retirés : « Que manger au Fouta ? » est une question de plats, pas d'adresses.
    "restaurant", "resto", "où manger", "ou manger",
    "where to eat", "where can i eat", "place to eat", "places to eat", "dining", "food court",
    "ouvert ce soir", "meilleur resto", "où se trouve", "ou se trouve",
    "prix", "tarif", "tarifs", "coût", "cout", "combien coûte", "combien coute",
    "price", "prices", "fare", "fares", "cost", "how much",
    "itinéraire", "itineraire", "trajet", "transport", "bus", "brt", "ter",
    # Bus Tata (AFTU) : jamais « tata » seul, qui veut d'abord dire « tante » (« ma tata habite à Rufisque »).
    "taxi", "péage", "peage", "car rapide", "dem dikk", "bus tata", "un tata", "le tata", "les tata", "les tatas", "en tata",
    "billet", "billets", "ticket", "tickets", "vol", "flight", "airline",
    "aéroport", "airport", "formalités", "formalites", "document", "documents",
    "ambassade", "consulat", "immigration", "vaccin", "vaccination",
    "banque", "bank", "guichet", "atm", "distributeur", "mobile money",
    "wave", "free money", "expresso money", "yas", "orange money",
    "concert", "festival", "match", "football", "salon", "foire",
    "programme", "program", "calendrier", "calendar", "fermé", "ferme", "closed",
    "urgent", "alerte", "grève", "greve", "perturbation", "incident",
)

# Faux amis : un sens courant sans rapport avec une information qui change. Ces expressions sont retirées
# du texte avant la recherche des déclencheurs ; le reste de la phrase compte toujours (« vérifie mon vol
# de demain » cherche encore : « vol », « demain »).
NEUTRAL_PHRASES = (
    # Écart fixe entre deux fuseaux, pas un horaire d'ouverture.
    "decalage horaire",
    # Commerce de quartier, pas un salon professionnel (foire, exposition).
    "salon de coiffure", "salons de coiffure", "salon de beaute", "salons de beaute", "salon de the",
    # Exploitation agricole, pas « fermé ».
    "une ferme", "ma ferme", "sa ferme", "la ferme", "les fermes", "des fermes", "notre ferme", "cette ferme",
    "ferme avicole", "fermes avicoles", "ferme agricole", "fermes agricoles", "ferme d'elevage", "ferme d elevage",
    # Faire connaître sa boutique, pas une promotion en cours chez un opérateur.
    "faire la promotion", "faire de la promotion", "faire sa promotion", "faire ma promotion",
    "promotion de ma", "promotion de mon", "promotion de mes", "promotion de notre", "promotion de nos",
    # Rédiger une offre pour ses clients, pas une offre en cours.
    "ecris une offre", "ecris moi une offre", "ecris-moi une offre", "ecrire une offre",
    "redige une offre", "redige moi une offre", "redige-moi une offre", "rediger une offre",
    # Règles de sa boutique, pas l'actualité politique.
    "politique de retour", "politique de retours", "politique de remboursement", "politique commerciale",
    "politique de confidentialite",
    # Relire son propre texte, pas vérifier une information du moment.
    "verifie mon", "verifie ma", "verifie mes", "verifie l'orthographe", "verifie l orthographe",
    "verifie ce texte", "verifie cette phrase", "verifie cette traduction", "check my", "verify my",
)

# Une fête religieuse ne demande le web que pour sa date (lunaire, annoncée chaque année) :
# « C'est quoi le Grand Magal ? » se raconte, « C'est quand le Magal cette année ? » se vérifie.
FEASTS = ("magal", "tabaski", "korite", "gamou", "ramadan", "careme")
FEAST_DATE_MARKERS = (
    "quand", "date", "dates", "quel jour", "when", "what day", "which day", "cette annee", "this year",
    "prochain", "prochaine", "next", "commence", "debut", "fin du", "fin de",
)
_YEAR = re.compile(r"(?<!\d)20\d\d(?!\d)")


def _without_neutral_phrases(text: str) -> str:
    return _compiled_term_pattern(NEUTRAL_PHRASES).sub(" ", text) if text else text


def should_use_web(message, context=""):
    lowered = _without_neutral_phrases(normalize(message).replace("’", "'"))
    # « exactement », « nouveau », « nouvelle » et « hier » seuls retirés : « c'est quoi exactement le thiéboudienne »,
    # « je suis nouveau à Dakar », « hier j'ai goûté le thiakry » ne demandent rien du moment.
    current_markers = (
        "verifie", "confirme", "a jour", "en ce moment",
        "pour aujourd'hui", "pour demain", "ce soir", "demain", "s'est passe hier", "s est passe hier",
        "latest", "current", "right now", "as of", "verify", "check",
        "actualite", "actualites", "news", "quoi de nouveau", "dernieres nouvelles",
    )
    if _contains_any(lowered, current_markers):
        return True
    if _contains_any(lowered, WEB_HINTS):
        return True
    live_entities = (
        "president", "presidente", "ministre", "maire", "depute",
        "gouvernement", "federation", "selectionneur", "club",
        "election", "elections", "loi", "decret", "parlement", "politique",
        "equipe nationale", "joueur", "chanteur", "artiste",
        "entreprise", "restaurant", "hotel",
    )
    if _contains_any(lowered, live_entities):
        return True

    # Intentions qui vieillissent vite, même sans « actuel » ou « aujourd'hui ».
    dynamic_intents = (
        "prix", "tarif", "cout", "coût", "horaire", "horaires",
        "ouvert", "ferme", "fermé", "disponible", "disponibilite", "disponibilité",
        "reservation", "réservation", "billet", "ticket", "vol", "ferry",
        "taxi", "bus", "transport", "aeroport", "aéroport", "aibd",
        "visa", "passeport", "formalites", "formalités", "démarche", "demarche",
        "sim", "esim", "forfait", "internet", "orange money", "wave",
        # « change » seul retiré (« qu'est-ce qui change entre… ») : seulement le change de monnaie.
        "free money", "mobile money", "paiement", "transfert",
        "bureau de change", "bureaux de change", "le change", "du change",
        "change euro", "change euros", "change dollar", "change dollars",
        "taux", "inflation", "population", "salaire", "impot", "impôt",
        "douane", "frontiere", "frontière", "securite", "sécurité",
        "alerte", "pluie", "meteo", "météo", "temperature", "température",
        "greve", "grève", "travaux", "route", "circulation", "manifestation",
        "concert", "evenement", "événement", "match", "resultat", "résultat",
        "classement", "promotion", "offre", "sante", "santé", "hopital", "hôpital", "pharmacie", "urgence", "vaccination",
        # Santé et premiers secours : alertes sanitaires, campagnes de moustiquaires, conseils qui évoluent.
        "paludisme", "palu", "malaria", "fievre", "fièvre", "moustique", "moustiques", "moustiquaire", "moustiquaires",
        "repulsif", "répulsif", "premiers secours", "deshydratation", "déshydratation", "diarrhee", "diarrhée",
        "morsure", "morsures", "piqure", "piqûre", "piqures", "piqûres", "brulure", "brûlure", "brulures", "brûlures",
        "serpent", "serpents", "scorpion", "intoxication alimentaire", "coup de chaleur", "insolation",
        # Ajouts du banc d'essai : réponses qui changent d'une année à l'autre.
        "hotels", "auberge", "auberges", "logement", "hebergement",
        "vaccin", "vaccins", "fievre jaune",
        "bateau", "chaloupe", "navette", "traversee",
        "cette annee", "cette semaine", "ce mois", "ce week-end", "ce weekend", "this year", "this week",
        # Prix demandé sans accent ni « coûte » collé à « combien » : « combien ça coûte ? ».
        "combien ca coute", "ca coute combien", "coute combien",
        "aides", "subvention", "subventions", "financement", "financements",
        "bourse", "bourses", "appel a projets", "appels a projets",
        # Démarches : les repères du site sont un point de départ, les règles et dates se vérifient en ligne.
        "carte d'identité", "carte d'identite", "carte d identite", "carte nationale", "extrait de naissance", "acte de naissance",
        "casier judiciaire", "jugement supplétif", "jugement suppletif", "woyofal", "senelec", "campusen",
        "couverture maladie", "ipres", "securite sociale", "sécurité sociale",
        # Arnaques et mobile money : les alertes, les opérateurs et les procédures de plainte changent souvent.
        "arnaque", "arnaques", "arnaquer", "arnaqueur", "arnaqueurs", "escroc", "escrocs", "escroquerie", "escroqueries",
        "fraude", "fraudes", "frauduleux", "frauduleuse", "scam", "scams", "phishing", "hameçonnage", "hameconnage",
        "faux billet", "faux billets", "fausse monnaie", "contrefaçon", "contrefacon", "faux sms", "faux visa",
        "faux visas", "usurpation", "sim swap", "code secret", "code otp", "reclamation", "réclamation",
        "yas money", "monnaie electronique", "monnaie électronique",
    )
    if _contains_any(lowered, dynamic_intents):
        return True
    if _contains_any(lowered, FEASTS) and (_contains_any(lowered, FEAST_DATE_MARKERS) or _YEAR.search(lowered)):
        return True
    # Un suivi comme « et demain ? » peut dépendre d'un sujet dynamique
    # présent dans le tour précédent.
    combined = _without_neutral_phrases(normalize(f"{context} {message}").replace("’", "'"))
    contextual_dynamic = (
        "meteo", "météo", "prix", "tarif", "cout", "coût", "horaire",
        "ouvert", "disponible", "reservation", "réservation", "billet",
        "vol", "ferry", "transport", "visa", "passeport", "sim", "esim",
        "forfait", "orange money", "wave", "taux", "securite",
        "sécurité", "alerte", "greve", "grève", "match", "concert",
        "evenement", "événement", "promotion", "offre",
    )
    return _contains_any(combined, contextual_dynamic)



def reasoning_effort(use_web: bool, planner: bool) -> str:
    if planner:
        return "low"
    if use_web:
        return "low"
    return "low"
