"""Réponses prêtes aux questions fréquentes, servies sans appeler le modèle.

Une question courte qui ne demande que les numéros d'urgence (« Numéro de la police ? ») reçoit tout
de suite les numéros vérifiés de la page /urgences (routes/emergency.py, source : ambassade de France au
Sénégal, relevés le 6 octobre 2026). Seuls 17, 18 et 1515 sont servis : la gendarmerie et SOS Médecins
sont à revérifier.

Une question courte qui ne demande qu'une conversion euro ↔ FCFA (« 100 euros en FCFA ? ») reçoit le calcul de
services/calculators.py, à la parité fixe 1 € = 655,957 FCFA (décision du propriétaire du 19 octobre 2026 : Teranga
répond seul à ce qu'il sait déjà calculer). Le dollar et la livre (taux variable) et l'anglais vont au modèle.

Une question qui donne la somme envoyée en euros et la somme reçue en FCFA (« J'ai envoyé 200 €, ma famille a reçu
128 000 FCFA ») reçoit l'écart avec la parité fixe, en FCFA, en euros et en pourcentage : ce que le change a coûté, en
plus des frais affichés. C'est un calcul, aucun taux ni frais n'est inventé. Le sens inverse (FCFA envoyés) va au modèle.

Une question courte sur l'heure à Dakar ou le décalage avec Paris reçoit l'heure du moment à Dakar (UTC+0 toute l'année,
repère vérifié) et l'écart actuel avec Paris (1 h ou 2 h, selon l'heure d'été française de la base des fuseaux). Une
question sur l'indicatif du Sénégal reçoit +221 (repère vérifié). « À quelle heure part le ferry ? » va au modèle.

Une question courte qui ne demande que la date d'une fête (« C'est quand la Tabaski ? ») reçoit la date du calendrier
vérifié (services/events.py), avec son statut : une fête lunaire non confirmée reste « estimée ».

Une question courte qui demande ce qu'est un plat, un en-cas, un dessert ou une boisson de la base (« C'est quoi le
yassa ? ») reçoit sa description, telle quelle, de data/senegal_knowledge.json.

Toute autre formulation (une situation, un lieu, une précision) va au modèle.
"""

from __future__ import annotations

import datetime as _dt
import re
from decimal import Decimal
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any

from routes.emergency import ADVICE, EMBASSY_LINKS, EMERGENCY_NUMBERS
from services.answer_cache import _has_earlier_turns
from services.calculators import (
    arrondir,
    calculation_block,
    eur_vers_fcfa,
    fcfa_vers_eur,
    format_montant,
    format_nombre,
    format_pourcent,
    montants_du_texte,
)
from services.events import _ALIASES, _asked, french_date, upcoming_events
from services.senegal_knowledge import load_senegal_knowledge
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
# Un opérateur de calcul n'est pas un mot : sans ce garde-fou, « 100 euros en FCFA * 2 » perdait son « * 2 ».
_OPERATORS = re.compile(r"[*/+×÷%^]|\d\s*-\s*\d|\s-\s")


def _conversion_line(message: str) -> str | None:
    """La ligne du calcul vérifié (« 100 € = 65 595,70 FCFA (…), parité fixe : … »), ou None."""
    if len(message) > MAX_CHARS or _OPERATORS.search(message):
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
        "Pour un transfert ou un change, comparez le montant reçu, frais compris : tout écart entre le taux annoncé et "
        "cette parité est un coût (marge ou commission de change), en plus des frais affichés.",
        "Convertisseur (euro, dollar, livre) : page d'accueil de teranga-ai.fr",
    ])


# Date d'une fête : un mot qui demande « quand », le nom de la fête et des mots qui ne changent pas la demande.
# Écart d'un transfert euro → FCFA. Le texte est déjà sans accents (montants_du_texte).
_TRANSFER_MAX_CHARS = 160
_SENT = re.compile(r"\b(?:envoy|envoi|transfer|vire|verse)\w*")
_RECEIVED = re.compile(r"\b(?:recu|recue|recus|recues|recoit|recoivent|recevoir|touche|touchee|touches|touchees|"
                       r"arrive|arrivee|arrives|arrivees|obtenu|obtenue)\b")


def _transfer_amounts(message: str) -> tuple[Decimal, Decimal] | None:
    """(euros envoyés, FCFA reçus) si la question donne exactement ces deux montants, sinon None."""
    if len(message) > _TRANSFER_MAX_CHARS:
        return None
    texte, montants = montants_du_texte(message)
    euros = [m for m in montants if m.devise == "EUR"]
    fcfa = [m for m in montants if m.devise == "XOF"]
    if len(montants) != 2 or len(euros) != 1 or len(fcfa) != 1:
        return None
    euro, recu = euros[0], fcfa[0]
    if not euro.valeur or recu.valeur is None:
        return None
    sent = [m.start() for m in _SENT.finditer(texte)]
    received = [m.start() for m in _RECEIVED.finditer(texte)]
    if not sent or not received:
        return None

    def distance(montant, positions):
        return min(abs(position - montant.debut) for position in positions)

    # Chaque montant va avec le verbe le plus proche : les euros envoyés, les FCFA reçus. Sinon (FCFA envoyés,
    # euros reçus), c'est l'autre sens : le modèle répond.
    if distance(euro, sent) > distance(euro, received) or distance(recu, received) > distance(recu, sent):
        return None
    # Bien plus que la parité : montants mal lus ou autre situation, le modèle répond.
    if recu.valeur > eur_vers_fcfa(euro.valeur) * Decimal("1.05"):
        return None
    return euro.valeur, recu.valeur


def _transfer_reply(euros: Decimal, recu: Decimal) -> str:
    attendu = eur_vers_fcfa(euros)
    lines = [f"Au taux officiel (parité fixe 1 € = 655,957 FCFA), {format_montant(euros, 'EUR')} = "
             f"{format_nombre(attendu, 0)} FCFA."]
    ecart = arrondir(attendu - recu, 0)
    if ecart == 0:
        return "\n".join(lines + [
            f"Montant reçu : {format_montant(recu, 'XOF')}. Il correspond à la parité : le change ne vous a rien coûté.",
            "Le coût du transfert se limite alors aux frais payés à l'envoi.",
        ])
    if ecart < 0:  # reçu au-dessus de la parité (jusqu'à 5 %) : on le dit tel quel
        return "\n".join(lines + [
            f"Montant reçu : {format_montant(recu, 'XOF')}, soit {format_nombre(-ecart)} FCFA de plus que la valeur à "
            "la parité : le change ne vous a rien coûté.",
            "Le coût du transfert se limite alors aux frais payés à l'envoi.",
        ])
    perte = euros - fcfa_vers_eur(recu)
    return "\n".join(lines + [
        f"Montant reçu : {format_montant(recu, 'XOF')}, soit {format_nombre(ecart)} FCFA de moins "
        f"({format_montant(perte, 'EUR')}, {format_pourcent(perte / euros * 100)} de la somme envoyée).",
        "Cet écart est un coût du change (marge ou commission), en plus des frais payés à l'envoi.",
        "Pour comparer deux services : regardez le montant reçu en FCFA pour la même somme envoyée, frais compris.",
    ])


# Heure de Dakar et décalage avec Paris (sujet « heure » de practical_facts : UTC+0 toute l'année, sans changement
# d'heure). L'heure du moment et l'heure d'été française viennent de la base des fuseaux (zoneinfo + tzdata).
_TIME_WORDS = {"heure", "heures", "decalage", "horaire", "fuseau"}
_TIME_ALLOWED = _TIME_WORDS | _FILLER_WORDS | {
    "paris", "france", "entre", "et", "avec", "maintenant", "actuellement", "moment", "y", "t", "fait", "qu", "on",
}


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _asked_time(message: str) -> bool:
    """« Quelle heure est-il à Dakar ? », « Décalage horaire Sénégal ? » ; pas « À quelle heure part le ferry ? »."""
    if len(message) > MAX_CHARS:
        return False
    words = re.findall(r"[a-z0-9]+", fold_text(message).lower())
    if not words or any(word not in _TIME_ALLOWED for word in words) or not _TIME_WORDS.intersection(words):
        return False
    return bool({"decalage", "fuseau", "dakar", "senegal"}.intersection(words))


def _time_reply(now: _dt.datetime) -> str | None:
    try:
        dakar = now.astimezone(ZoneInfo("Africa/Dakar"))
        paris = now.astimezone(ZoneInfo("Europe/Paris"))
    except ZoneInfoNotFoundError:
        return None  # base des fuseaux absente : le modèle répond avec le repère vérifié
    ecart = round((paris.utcoffset() - dakar.utcoffset()).total_seconds() / 3600)
    if dakar.utcoffset() != _dt.timedelta(0) or ecart not in (1, 2):
        return None
    saison = "heure d'été" if ecart == 2 else "heure d'hiver"
    return "\n".join([
        f"À Dakar, il est {dakar.hour} h {dakar.minute:02d} (heure du Sénégal, UTC+0).",
        f"En ce moment, il y a {ecart} h de moins qu'à Paris ({saison} en France).",
        "Le Sénégal ne change jamais d'heure : 1 h de moins que Paris en hiver, 2 h de moins en été.",
    ])


# Indicatif téléphonique (sujet « sim » de practical_facts : « Indicatif : +221 »).
_PHONE_CODE_ALLOWED = _FILLER_WORDS | {"indicatif", "telephonique", "telephone", "international", "pays"}
_PHONE_CODE_REPLY = "L'indicatif téléphonique du Sénégal est +221.\nDepuis l'étranger, composez +221 puis le numéro."


def _asked_phone_code(message: str) -> bool:
    if len(message) > MAX_CHARS:
        return False
    words = re.findall(r"[a-z0-9]+", fold_text(message).lower())
    return ("indicatif" in words and bool({"senegal", "dakar"}.intersection(words))
            and all(word in _PHONE_CODE_ALLOWED for word in words))


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


# Plat de la base : un mot qui demande « c'est quoi », le nom du plat et des mots qui ne changent pas la demande.
_WHAT_WORDS = {"quoi", "qu", "definition", "signifie", "explique"}
# Un ingrédient seul n'est pas le plat : « C'est quoi le gingembre ? » ne parle pas forcément du jus.
_INGREDIENT_ALIASES = {"gingembre", "hibiscus"}


def _folded(text: object) -> str:
    return fold_text(str(text or "")).lower().strip()


@lru_cache(maxsize=1)
def _dish_index() -> tuple[tuple[tuple[re.Pattern, dict], ...], frozenset]:
    """(motif du nom, plat) pour chaque plat décrit dans la base, et les mots de leurs noms ; chargés une fois."""
    entries, name_words = [], set()
    for dish in load_senegal_knowledge().get("dishes", []):
        if not isinstance(dish, dict) or not dish.get("name") or not dish.get("text"):
            continue
        names = {_folded(name) for name in [dish["name"], *(dish.get("aliases") or [])]} - _INGREDIENT_ALIASES - {""}
        for name in names:
            name_words.update(re.findall(r"[a-z0-9]+", name))
        pattern = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
                             + r")(?![a-z0-9])")
        entries.append((pattern, dish))
    return tuple(entries), frozenset(name_words)


def _asked_dish(message: str) -> dict | None:
    """Le seul plat de la base dont la question demande ce qu'il est, ou None."""
    if len(message) > MAX_CHARS:
        return None
    folded = _folded(message)
    words = re.findall(r"[a-z0-9]+", folded)
    if not _WHAT_WORDS.intersection(words):
        return None
    entries, name_words = _dish_index()
    allowed = _WHAT_WORDS | name_words | _FILLER_WORDS | {"que", "moi", "un", "une", "ca", "veut", "dire"}
    if any(word not in allowed for word in words):
        return None
    found = [dish for pattern, dish in entries if pattern.search(folded)]
    return found[0] if len(found) == 1 else None


def _dish_reply(dish: dict) -> str:
    lines = [f"{dish['name']} — {dish.get('kind') or 'spécialité'}", dish["text"]]
    if dish.get("where"):
        lines.append(f"Où : {dish['where']}.")
    lines.append("Toutes les spécialités : teranga-ai.fr/specialites-senegal")
    return "\n".join(lines)


# « Que peux-tu faire ? », « Qui es-tu ? » : rien dans le contexte de l'IA ne décrit le service, qui risquait d'inventer
# des fonctions (relevé /stats-ia du 24 octobre 2026). Chaque page citée existe (tests/test_reponse_seule_presentation.py
# l'ouvre). Teranga s'adresse à toute la population : Sénégalais au pays, diaspora, commerçants et voyageurs.
_ABOUT = re.compile(
    r"(?<![a-z])(?:qui es tu|tu es qui|qui etes vous|vous etes qui|"
    r"(?:que|qu est ce que) (?:tu |vous )?(?:peux|sais|pouvez|savez) (?:tu |vous )?faire|tu (?:peux|sais) faire quoi|"
    r"tu sers a quoi|a quoi tu sers|a quoi sert teranga|c est quoi teranga|qu est ce que teranga|"
    r"presente toi|presentez vous|comment (?:tu peux|peux tu|pouvez vous) m aider)(?![a-z])"
)
_ABOUT_ALLOWED = _FILLER_WORDS | {
    "es", "etes", "tu", "toi", "vous", "que", "qu", "quoi", "peux", "sais", "pouvez", "savez", "faire", "sers", "sert",
    "teranga", "ai", "ia", "presente", "presentez", "comment", "m", "aider", "exactement", "concretement", "alors",
    "donc", "et", "ici", "dis", "moi",
}
_ABOUT_REPLY = "\n".join([
    "Je suis Teranga AI, l'assistant du Sénégal, pour tout le monde : les Sénégalais au pays, la diaspora, "
    "les commerçants et les voyageurs.",
    "Je réponds aux questions de tous les jours : démarches, santé, argent, transport, téléphone, emploi, études, "
    "création d'entreprise, mais aussi culture, histoire, cuisine et lieux à visiter.",
    "Vous pouvez aussi :",
    "- me parler avec le micro et écouter la réponse ;",
    "- convertir des euros en francs CFA ;",
    "- trouver les numéros d'urgence : teranga-ai.fr/urgences",
    "- voir les dates des fêtes : teranga-ai.fr/calendrier-fetes-senegal",
    "- préparer un voyage jour par jour : teranga-ai.fr/trip-planner",
    "- découvrir les lieux à visiter : teranga-ai.fr/lieux",
    "Posez votre question en français, en anglais ou en wolof.",
])


def _asked_about_teranga(message: str) -> bool:
    if len(message) > MAX_CHARS:
        return False
    folded = _folded(message)
    words = re.findall(r"[a-z0-9]+", folded)
    return bool(words) and all(word in _ABOUT_ALLOWED for word in words) and bool(_ABOUT.search(" ".join(words)))


def quick_answer(payload: dict[str, Any], raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Réponse prête ({reply, sources}) au format du cache des réponses, ou None (le modèle répond).

    « theme » : le seul thème de /stats-ia que la réponse couvre (services/coverage_log.py)."""
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
        return {"reply": _emergency_reply(language), "sources": list(_SOURCES), "image": None, "map": None, "theme": "urgences"}
    if language == "fr":
        line = _conversion_line(message)
        if line:
            return {"reply": _conversion_reply(line), "sources": [], "image": None, "map": None, "theme": "argent"}
        transfer = _transfer_amounts(message)
        if transfer:
            return {"reply": _transfer_reply(*transfer), "sources": [], "image": None, "map": None, "theme": "argent"}
        if _asked_time(message):
            reply = _time_reply(_now_utc())
            if reply:
                return {"reply": reply, "sources": [], "image": None, "map": None, "theme": "voyage"}
        if _asked_phone_code(message):
            return {"reply": _PHONE_CODE_REPLY, "sources": [], "image": None, "map": None, "theme": "internet"}
        if _asked_about_teranga(message):
            return {"reply": _ABOUT_REPLY, "sources": [], "image": None, "map": None, "theme": "teranga_ai"}
        event = _asked_holiday(message)
        if event:
            return {"reply": _holiday_reply(event), "sources": [], "image": None, "map": None, "theme": "fetes"}
        dish = _asked_dish(message)
        if dish:
            return {"reply": _dish_reply(dish), "sources": [], "image": None, "map": None, "theme": "cuisine"}
    return None
