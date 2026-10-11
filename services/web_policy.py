"""Web retrieval policy for Teranga AI V3.1.

Keeps web quality and latency decisions outside the Flask route so they can be
tested without loading the full application.
"""
from __future__ import annotations

import re
from functools import lru_cache

from services.validation import normalize

# Le filtre de domaines (« allowed_domains » de l'outil de recherche web) n'est dur que lorsque la réponse EST une
# information officielle : statistiques, démarches, météo. Pour un restaurant, un horaire de TER, un prix ou un voyage,
# les sites de l'État ne contiennent pas la réponse : ces sujets ne sont plus limités (les domaines de référence
# restent demandés au modèle par la ligne « POLITIQUE DE SOURCES » du contexte, sans exclure le reste du web).
# « gouv.sn » couvre tous les ministères (sante.gouv.sn, education.gouv.sn, sec.gouv.sn…), pas seulement ceux nommés.
SOURCE_FILTERS = {
    "society": ("ansd.sn", "gov.sn", "who.int", "worldbank.org", "gouv.sn"),
    "agriculture": ("ansd.sn", "agriculture.gouv.sn", "gov.sn", "fao.org", "gouv.sn"),
    "territory": ("ansd.sn", "gov.sn", "tourisme.gouv.sn", "gouv.sn"),
    "administration": ("diplomatie.gouv.sn", "interieur.gouv.sn", "gov.sn", "gouv.sn"),
    "weather": ("anacim.sn", "ansd.sn", "gov.sn"),
}

# Un mot de 4 lettres ou plus accepte le pluriel (« vols », « restaurants », « pharmacies »), sauf quand le pluriel
# change de sens (« la ferme » ≠ « les fermes »).
_NO_PLURAL = frozenset({"ferme"})


def _term_regex(term: str) -> str:
    plural = len(term) >= 4 and term[-1].isalpha() and term[-1] not in "sx" and term not in _NO_PLURAL
    return re.escape(term) + ("s?" if plural else "")


@lru_cache(maxsize=32)
def _compiled_term_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = "|".join(
        _term_regex(term)
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
    "actualité", "actualités", "news", "today", "now",
    "current", "latest", "recent", "schedule", "hours",
    "open", "available", "availability", "booking", "weather", "event",
    "visa", "ferry", "cfa", "taux de change", "taux",
    "sim", "orange money", "week-end", "weekend", "ce soir", "demain",
    "manger", "restaurant", "resto", "où manger", "ou manger",
    "eat", "dining", "food court",
    "ouvert ce soir", "meilleur resto", "où se trouve", "ou se trouve",
    "prix", "tarif", "tarifs", "coût", "cout", "combien coûte", "combien coute",
    "price", "prices", "fare", "fares", "cost", "how much",
    "itinéraire", "itineraire", "trajet", "transport", "bus", "brt", "ter",
    "taxi", "péage", "peage", "car rapide", "dem dikk", "tata",
    "billet", "billets", "ticket", "tickets", "vol", "flight", "airline",
    "aéroport", "airport", "formalités", "formalites", "document", "documents",
    "ambassade", "consulat", "immigration", "vaccin", "vaccination",
    "banque", "bank", "guichet", "atm", "distributeur", "mobile money",
    "wave", "free money", "expresso money", "yas", "orange money",
    "concert", "festival", "match", "football", "salon", "foire",
    "programme", "program", "calendrier", "calendar", "fermé", "ferme", "closed",
    "urgent", "alerte", "grève", "greve", "perturbation", "incident",
)

def should_use_web(message, context=""):
    lowered = normalize(message)
    current_markers = (
        "verifie", "confirme", "a jour", "exactement", "en ce moment",
        "pour aujourd'hui", "pour demain", "ce soir", "demain", "hier",
        "latest", "current", "right now", "as of", "verify", "check",
        "actualite", "actualites", "news", "nouveau", "nouvelle",
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
        "free money", "mobile money", "paiement", "transfert", "change",
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
        "magal", "tabaski", "korite", "gamou", "ramadan", "careme",
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
        # (Le texte de la question est mis en minuscules sans accents avant la recherche ; seules les apostrophes
        # droite et courbe restent distinctes.)
        # Impôts, salaires et frais fixés par la loi ou par décret, loyers : les montants changent.
        "tva", "smig", "smag", "salaire minimum", "frais", "loyer moyen", "loyers", "coute", "coutent",
        # Alertes sanitaires et épidémies (comme le paludisme plus haut).
        "dengue", "cholera", "epidemie", "ebola", "mpox", "covid", "rougeole", "meningite",
        # Perturbations du quotidien : circulation, électricité, eau, manifestations.
        "embouteillage", "delestage", "penurie", "manif", "manifs",
        "coupure d'electricite", "coupures d'electricite", "coupure d’electricite", "coupures d’electricite",
        "coupure de courant", "coupures de courant", "panne de courant", "pannes de courant",
        "panne d'electricite", "panne d’electricite", "coupure d'eau", "coupure d’eau",
        # Emploi, concours, calendrier scolaire.
        "recrutement", "concours", "bfem", "annee scolaire", "rentree scolaire",
        # Voyage et argent : vols d'avion (« vols » seul parle aussi de cambriolages), compagnies, change, opérateurs,
        # transferts, papiers, avis aux voyageurs.
        "vols pour", "vols vers", "vols directs", "vols depuis", "vols entre", "vols annules", "vols low cost",
        "compagnie aerienne", "compagnies aeriennes", "operateur", "permis de conduire", "papiers",
        "western union", "moneygram", "worldremit",
        "changer mes euros", "changer des euros", "changer de l'argent", "changer de l’argent", "changer mon argent",
        "changer mes dollars", "changer des dollars",
        "consignes de voyage", "conseils aux voyageurs", "avis aux voyageurs",
        # Sport et pouvoirs publics.
        "entraineur", "joue quand", "jouent quand", "quand joue", "quand jouent", "prochain match", "qui dirige",
        # Sujets des repères sourcés (code du travail, état civil, santé publique, campagne agricole, pêche, jeunes) :
        # les règles et les dates se vérifient en ligne ; chaque mot est donné avec et sans accents.
        "code du travail", "licenciement", "conge de maternite", "congé de maternité", "inspection du travail",
        "declaration de naissance", "déclaration de naissance",
        "mutuelle de sante", "mutuelle de santé", "assurance maladie universelle",
        "code de la securite sociale", "code de la sécurité sociale", "cesarienne", "césarienne", "dialyse",
        "poste de sante", "poste de santé",
        "campagne agricole", "semences", "engrais", "permis de peche", "permis de pêche", "repos biologique",
        "bons de formation", "3fpt", "anpej", "nano-credit", "nano-crédit",
    )
    if _contains_any(lowered, dynamic_intents):
        return True
    # Un suivi comme « et demain ? » peut dépendre d'un sujet dynamique
    # présent dans le tour précédent.
    combined = normalize(f"{context} {message}")
    contextual_dynamic = (
        "meteo", "météo", "prix", "tarif", "cout", "coût", "horaire",
        "ouvert", "disponible", "reservation", "réservation", "billet",
        "vol", "ferry", "transport", "visa", "passeport", "sim", "esim",
        "forfait", "orange money", "wave", "taux", "change", "securite",
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
