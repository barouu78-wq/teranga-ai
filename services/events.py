"""Calendrier des fêtes et grands événements du Sénégal.

Les fêtes musulmanes suivent le calendrier lunaire : leur date est estimée puis
fixée quelques jours avant par la commission nationale d'observation du croissant
lunaire (CONACOC) ou par les familles religieuses. Sources (octobre 2026) :
Gamou 2026 fixé au 25 août (Le Soleil), Magal 2027 prévu le 23 juillet (prévision
astronomique relayée par Senegal7), Festival de jazz de Saint-Louis 2027 du 4 au
8 mai (au-senegal.com). Dates chrétiennes calculées depuis Pâques 2027 (28 mars).
"""

from __future__ import annotations

import datetime as _dt

from services.text import fold_text

# (date de début, date de fin ou None, nom, lieu, type, date confirmée ?, conseils)
EVENTS = (
    (_dt.date(2026, 8, 2), None, "Grand Magal de Touba", "Touba", "religious", True,
     "Des millions de pèlerins : routes vers Touba très chargées, hébergement souvent chez l'habitant. Tenue couverte et respect des consignes de la ville sainte."),
    (_dt.date(2026, 8, 25), None, "Gamou (Maouloud)", "Tivaouane, Ndiassane, Médina Baye", "religious", True,
     "Nuit de prières et de chants à Tivaouane ; jour férié. Prévoir des trajets longs vers Tivaouane la veille."),
    (_dt.date(2026, 11, 1), None, "Toussaint", "Tout le pays", "holiday", True,
     "Jour férié : administrations et banques fermées."),
    (_dt.date(2026, 12, 25), None, "Noël", "Tout le pays", "holiday", True,
     "Jour férié, ambiance festive à Dakar, Ziguinchor et dans les quartiers chrétiens. Hôtels de la Petite Côte très demandés."),
    (_dt.date(2027, 1, 1), None, "Jour de l'an", "Tout le pays", "holiday", True,
     "Jour férié. Les plages et la Petite Côte sont très fréquentées pendant les fêtes."),
    (_dt.date(2027, 3, 10), None, "Korité (Aïd el-Fitr)", "Tout le pays", "religious", False,
     "Fin du Ramadan : prière le matin puis visites familiales. Commerces et transports perturbés, cars pleins la veille."),
    (_dt.date(2027, 3, 29), None, "Lundi de Pâques", "Tout le pays", "holiday", True,
     "Jour férié. Le dimanche, partage du ngalax (dessert au mil et à l'arachide) entre voisins."),
    (_dt.date(2027, 4, 4), None, "Fête de l'Indépendance", "Dakar et tout le pays", "national", True,
     "Défilé à Dakar le matin : circulation coupée autour du centre. Drapeaux et animations partout."),
    (_dt.date(2027, 5, 1), None, "Fête du travail", "Tout le pays", "holiday", True,
     "Jour férié, défilés des syndicats."),
    (_dt.date(2027, 5, 4), _dt.date(2027, 5, 8), "Festival international de jazz de Saint-Louis", "Saint-Louis", "festival", True,
     "35e édition. Réserve l'hébergement tôt : la ville est pleine pendant le festival."),
    (_dt.date(2027, 5, 6), None, "Ascension", "Tout le pays", "holiday", True,
     "Jour férié : administrations et banques fermées."),
    (_dt.date(2027, 5, 17), None, "Tabaski (Aïd el-Kébir)", "Tout le pays", "religious", False,
     "Grande fête du mouton : départs massifs vers les régions 2 à 3 jours avant, transports chers et rares, Dakar se vide. Lundi de Pentecôte le même jour."),
    (_dt.date(2027, 6, 16), None, "Tamkharit (Achoura)", "Tout le pays", "religious", False,
     "Le soir, couscous en famille ; les enfants se déguisent et passent de maison en maison (tadjabone)."),
    (_dt.date(2027, 7, 23), None, "Grand Magal de Touba", "Touba", "religious", False,
     "Des millions de pèlerins : routes vers Touba très chargées, hébergement souvent chez l'habitant. Tenue couverte et respect des consignes de la ville sainte."),
    (_dt.date(2027, 8, 15), None, "Assomption", "Tout le pays", "holiday", True,
     "Jour férié ; pèlerinage marial de Popenguine à la Pentecôte, fête à l'Assomption dans les paroisses."),
    (_dt.date(2027, 8, 15), None, "Gamou (Maouloud)", "Tivaouane, Ndiassane, Médina Baye", "religious", False,
     "Nuit de prières et de chants à Tivaouane ; jour férié. Prévoir des trajets longs vers Tivaouane la veille."),
)

TYPE_LABELS = {"religious": "Fête religieuse", "national": "Fête nationale", "holiday": "Jour férié", "festival": "Festival"}
_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def french_date(day: _dt.date) -> str:
    return f"{day.day} {_MONTHS[day.month - 1]} {day.year}"


def upcoming_events(today: _dt.date | None = None, limit: int | None = None) -> list[dict]:
    """Événements en cours ou à venir, du plus proche au plus lointain."""
    today = today or _dt.date.today()
    items = []
    for start, end, name, place, kind, confirmed, tips in sorted(EVENTS, key=lambda e: e[0]):
        if (end or start) < today:
            continue
        items.append({
            "start": start, "end": end, "name": name, "place": place, "kind": kind,
            "confirmed": confirmed, "tips": tips, "days_left": (start - today).days,
        })
    return items[:limit] if limit else items


# Autres noms par lesquels on désigne une fête (« Aïd », « jazz », « fête du mouton »…).
_ALIASES = {
    "Tabaski": ("tabaski", "aid el kebir", "aid al adha", "mouton", "eid al adha"),
    "Korité": ("korite", "aid el fitr", "eid al fitr", "fin du ramadan", "end of ramadan"),
    "Grand Magal": ("magal",),
    "Gamou": ("gamou", "maouloud", "mawlid", "mouloud"),
    "Tamkharit": ("tamkharit", "achoura", "ashura"),
    "jazz": ("jazz",),
    "Indépendance": ("independance", "independence", "4 avril"),
    "Noël": ("noel", "christmas"),
    "Pâques": ("paques", "easter"),
    "Toussaint": ("toussaint",),
    "Ascension": ("ascension",),
    "Assomption": ("assomption", "assumption"),
}


_fold = fold_text


def _asked(event: dict, query: str) -> bool:
    """La question nomme-t-elle cet événement ?"""
    if not query:
        return False
    for key, words in _ALIASES.items():
        if key.casefold() in event["name"].casefold() and any(w in query for w in words):
            return True
    return False


def events_context(today: _dt.date | None = None, query: str = "") -> str:
    """Bloc court pour l'assistant : les prochaines fêtes, avec le statut de la date.

    Les 6 plus proches, plus toute fête nommée dans la question même si elle est plus
    lointaine (« C'est quand la Tabaski ? » en octobre)."""
    folded = _fold(query)
    upcoming = upcoming_events(today)
    chosen = upcoming[:6] + [e for e in upcoming[6:] if _asked(e, folded)]
    lines = ["PROCHAINES FÊTES ET ÉVÉNEMENTS AU SÉNÉGAL (dates lunaires estimées tant que non confirmées) :"]
    for event in chosen:
        when = french_date(event["start"]) + (f" au {french_date(event['end'])}" if event["end"] else "")
        status = "confirmée" if event["confirmed"] else "estimée, à confirmer"
        lines.append(f"- {event['name']} ({event['place']}) : {when} [{status}]. {event['tips']}")
    return "\n".join(lines)
