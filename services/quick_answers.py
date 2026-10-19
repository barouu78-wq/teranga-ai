"""Réponses prêtes aux questions fréquentes, servies sans appeler le modèle.

Une question courte qui ne demande que les numéros d'urgence (« Numéro de la police ? ») reçoit tout
de suite les numéros vérifiés de la page /urgences (routes/emergency.py, source : ambassade de France au
Sénégal, relevés le 6 octobre 2026). Seuls 17, 18 et 1515 sont servis : la gendarmerie et SOS Médecins
sont à revérifier.

Une question courte qui ne demande qu'une conversion euro ↔ FCFA (« 100 euros en FCFA ? ») reçoit le calcul de
services/calculators.py, à la parité fixe 1 € = 655,957 FCFA (décision du propriétaire du 19 octobre 2026 : Teranga
répond seul à ce qu'il sait déjà calculer). Le dollar et la livre (taux variable) et l'anglais vont au modèle.

Une question courte qui ne demande que la date d'une fête (« C'est quand la Tabaski ? ») reçoit la date du calendrier
vérifié (services/events.py), avec son statut : une fête lunaire non confirmée reste « estimée ».

Toute autre formulation (une situation, un lieu, une précision) va au modèle.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any

from routes.emergency import ADVICE, EMBASSY_LINKS, EMERGENCY_NUMBERS
from services.answer_cache import _has_earlier_turns
from services.calculators import calculation_block
from services.events import _ALIASES, _asked, french_date, upcoming_events
from services.text import fold_text

MAX_CHARS = 80
_NUMBER_WORDS = {"numero", "numeros", "num", "tel", "telephone", "appeler", "number", "numbers", "call"}
_SERVICE_WORDS = {"urgence", "urgences", "police", "pompier", "pompiers", "samu", "secours",
                  "emergency", "emergencies", "ambulance"}
# Mots qui ne changent pas la demande. Un mot hors de cette liste (un lieu précis, une situation) : le modèle répond.
_FILLER_WORDS = {
    "quel", "quels", "quelle", "quelles", "est", "sont", "c", "ce", "le", "la", "les", "l", "de", "d", "du", "des",
    "au", "a", "en", "pour", "qui", "cas", "s", "il", "te", "vous", "plait", "stp", "svp", "bonjour", "merci",
    "senegal", "dakar", "what", "is", "are", "the", "in", "for", "who", "to", "please", "hi", "hello",
    "fire", "brigade", "department", "service", "services", "medical", "medicale",
}
_ALLOWED = _NUMBER_WORDS | _SERVICE_WORDS | _FILLER_WORDS
_LABELS_EN = {"17": "Police", "18": "Fire brigade", "1515": "SAMU (medical emergency)"}
_SOURCES = [{"title": "Ambassade de France au Sénégal", "url": EMBASSY_LINKS[0][1]}]


def _asks_emergency_numbers(message: str) -> bool:
    if len(message) > MAX_CHARS:
        return False
    words = re.findall(r"[a-z0-9]+", fold_text(message).lower())
    return (
        bool(words)
        and set(words) <= _ALLOWED
        and bool(_SERVICE_WORDS.intersection(words))
        and bool(_NUMBER_WORDS.intersection(words))
    )


def _emergency_reply(language: str) -> str:
    national = [entry for entry in EMERGENCY_NUMBERS if entry[0] in _LABELS_EN]
    if language == "en":
        lines = ["Emergency numbers in Senegal, free from any phone, even without credit:"]
        lines += [f"- {_LABELS_EN[shown]}: {shown}" for shown, _, _, _ in national]
        lines += ["", "Give the exact place first (neighbourhood, landmark, hotel name), then what is happening.",
                  "All useful numbers, readable offline: teranga-ai.fr/urgences"]
    else:
        lines = ["Numéros d'urgence au Sénégal, gratuits depuis tous les téléphones, même sans crédit :"]
        lines += [f"- {service} : {shown}" for shown, _, service, _ in national]
        lines += ["", ADVICE[1], "Tous les numéros utiles, lisibles hors connexion : teranga-ai.fr/urgences"]
    return "\n".join(lines)


# Conversion euro ↔ FCFA : une devise à parité fixe, des nombres et des mots qui ne changent pas la demande.
_FIXED_CURRENCY_WORDS = {"euro", "euros", "eur", "fcfa", "cfa", "xof", "franc", "francs"}
_CONVERSION_WORDS = _FIXED_CURRENCY_WORDS | {
    "convertir", "conversion", "combien", "font", "fait", "vaut", "valent", "egal", "egale", "egalent",
    "donne", "donnent", "mille", "million", "millions", "un", "une", "ca",
} | _FILLER_WORDS


def _conversion_line(message: str) -> str | None:
    """La ligne du calcul vérifié (« 100 € = 65 595,70 FCFA (…), parité fixe : … »), ou None."""
    if len(message) > MAX_CHARS:
        return None
    words = re.findall(r"[a-z0-9]+", fold_text(message).lower())
    if not any(word.isdigit() for word in words) or not _FIXED_CURRENCY_WORDS.intersection(words):
        return None
    if any(not word.isdigit() and word not in _CONVERSION_WORDS for word in words):
        return None
    lines = [line[2:] for line in calculation_block(message).splitlines() if line.startswith("- ")]
    # Une seule conversion, à la parité fixe : sinon (plusieurs montants, autre calcul), le modèle répond.
    if len(lines) != 1 or "parité fixe : 1 € = 655,957 FCFA" not in lines[0]:
        return None
    return lines[0]


def _conversion_reply(line: str) -> str:
    return "\n".join([
        line,
        "Cette parité entre l'euro et le franc CFA est fixe : elle ne change pas d'un jour à l'autre.",
        "Pour un transfert ou un change, les frais et le taux appliqués par l'opérateur peuvent réduire la somme "
        "reçue : comparez avant d'envoyer.",
        "Convertisseur (euro, dollar, livre) : page d'accueil de teranga-ai.fr",
    ])


# Date d'une fête : un mot qui demande « quand », le nom de la fête et des mots qui ne changent pas la demande.
_WHEN_WORDS = {"quand", "date"}
_HOLIDAY_WORDS = {word for names in _ALIASES.values() for name in names for word in name.split()} | {
    "fete", "festival", "international", "grand", "saint", "louis", "touba",
}
_DATE_WORDS = _WHEN_WORDS | _HOLIDAY_WORDS | _FILLER_WORDS | {
    "prochain", "prochaine", "tombe", "sera", "cette", "annee", "que",
}


def _today() -> _dt.date:
    return _dt.date.today()


def _asked_holiday(message: str) -> dict | None:
    """La prochaine occurrence de la seule fête dont la question demande la date, ou None."""
    if len(message) > MAX_CHARS:
        return None
    folded = fold_text(message).lower()
    words = re.findall(r"[a-z0-9]+", folded)
    if not _WHEN_WORDS.intersection(words):
        return None
    years = {int(word) for word in words if word.isdigit() and len(word) == 4}
    if any(word not in _DATE_WORDS and not (word.isdigit() and len(word) == 4) for word in words):
        return None
    # « 4 avril » (Indépendance) est le seul nom de fête avec un nombre : déjà couvert par « independance ».
    named = {}
    for event in upcoming_events(_today()):
        if _asked(event, folded):
            named.setdefault(event["name"], event)
    if len(named) != 1:
        return None
    (event,) = named.values()
    if years and years != {event["start"].year}:
        return None
    return event


def _holiday_reply(event: dict) -> str:
    when = french_date(event["start"]) + (f" au {french_date(event['end'])}" if event["end"] else "")
    days = event["days_left"]
    soon = "aujourd'hui" if days <= 0 else ("demain" if days == 1 else f"dans {days} jours")
    lines = [f"{event['name']} : {when} ({soon})."]
    if event["place"] != "Tout le pays":
        lines.append(f"Lieu : {event['place']}.")
    if event["confirmed"]:
        lines.append("Date confirmée.")
    else:
        lines.append("Date estimée : les fêtes musulmanes suivent le calendrier lunaire, et la date exacte est fixée "
                     "quelques jours avant, à l'observation du croissant de lune.")
    lines += [event["tips"], "Toutes les fêtes de l'année : teranga-ai.fr/calendrier-fetes-senegal"]
    return "\n".join(lines)


def quick_answer(payload: dict[str, Any], raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Réponse prête ({reply, sources}) au format du cache des réponses, ou None (le modèle répond)."""
    raw = raw if isinstance(raw, dict) else {}
    language = str(payload.get("language") or "fr")
    message = str(payload.get("message") or "")
    if language not in ("fr", "en") or payload.get("photo_only"):
        return None
    if _has_earlier_turns(raw.get("history"), message):
        return None
    if any(str(raw.get(name) or "").strip() for name in ("context_place", "trip_context", "trip_edit_request")):
        return None
    if _asks_emergency_numbers(message):
        return {"reply": _emergency_reply(language), "sources": list(_SOURCES), "image": None, "map": None}
    if language == "fr":
        line = _conversion_line(message)
        if line:
            return {"reply": _conversion_reply(line), "sources": [], "image": None, "map": None}
        event = _asked_holiday(message)
        if event:
            return {"reply": _holiday_reply(event), "sources": [], "image": None, "map": None}
    return None
