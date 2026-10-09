"""Mode autonome : réponse de secours quand l'IA est indisponible (panne, quota, délai dépassé).

Chaîne de repli : OpenAI, puis Claude si la clé Anthropic existe (voir services/backup_ai.py), puis
ce module : Teranga répond avec sa propre base vérifiée, sans appel réseau. Les faits sont repris
TELS QUELS (aucune reformulation, aucun fait ajouté) :

- le lieu ou le plat cité dans la question (data/senegal_knowledge.json) ;
- les prochaines fêtes du calendrier (services/events.py) quand la question en parle, avec le statut
  de la date : les dates lunaires restent marquées « estimée » ;
- les repères pratiques vérifiés qui correspondent (services/practical_facts.py : urgences, santé,
  argent, papiers…), 3 sujets au plus et un plafond de caractères, repère par repère.

Quand rien ne correspond, `knowledge_fallback(..., always=True)` ne renvoie pas None mais un message
honnête (pas de réponse prête, jamais d'invention) avec les pages utiles du site, et les numéros
d'urgence seulement si la question touche à une urgence. Une urgence reçoit toujours ce message, même
sans `always` : jamais une erreur sèche quand quelqu'un a besoin d'un numéro. Texte brut : le chat
l'affiche tel quel.
"""

from __future__ import annotations

import datetime as _dt
import re

from services.events import _asked, french_date, upcoming_events
from services.places import mentioned_places
from services.practical_facts import TOPICS, matching_topics
from services.senegal_knowledge import _fold

MAX_TOPICS = 3  # sujets pratiques au plus (comme matching_topics)
MAX_CHARS = 3000  # caractères de repères au plus : on ajoute des repères entiers, jamais coupés
MAX_EVENTS = 3  # fêtes au plus

_INTRO = {
    "fr": "L'assistant IA est momentanément indisponible. Voici ce que je sais déjà :",
    "en": "The AI assistant is temporarily unavailable. Here is what I already know (in French):",
}
_OUTRO = {
    "fr": "Réessaie dans un moment pour une réponse complète et personnalisée.",
    "en": "Please try again in a moment for a complete answer.",
}

# Titre de chaque sujet de practical_facts.TOPICS (français, anglais). Un test vérifie qu'aucun sujet n'en manque.
_TITLES = {
    "urgences": ("Urgences et sécurité", "Emergencies and safety"),
    "sante": ("Santé", "Health"),
    "argent": ("Argent et paiements", "Money and payments"),
    "arnaques": ("Arnaques à éviter", "Scams to avoid"),
    "mobile_money": ("Mobile money", "Mobile money"),
    "sim": ("Téléphone et internet", "Phone and internet"),
    "electricite": ("Électricité", "Electricity"),
    "heure": ("Heure", "Time"),
    "visa": ("Entrée au Sénégal (visa)", "Entering Senegal (visa)"),
    "saison": ("Saisons", "Seasons"),
    "entreprise": ("Créer une activité", "Starting a business"),
    "transport": ("Transports", "Getting around"),
    "foncier": ("Terrain et immobilier", "Land and property"),
    "vente": ("Vendre et fixer ses prix", "Selling and pricing"),
    "papiers": ("Papiers et état civil", "Papers and civil registry"),
    "factures": ("Électricité prépayée (Woyofal)", "Prepaid electricity (Woyofal)"),
    "protection": ("Santé et protection sociale", "Health cover and social protection"),
    "etudes": ("Études et bourses", "Studies and grants"),
    "langue": ("Langues", "Languages"),
}
_DEFAULT_TITLE = ("Repères pratiques", "Practical facts")
_EVENTS_TITLE = ("Prochaines fêtes et événements", "Upcoming holidays and events")
_FACTS = {name: facts for name, _, facts in TOPICS}

# Question de fêtes sans fête nommée (« quelles fêtes ? », « jours fériés ») : les prochaines du calendrier.
# Une fête privée (anniversaire, mariage…) n'est pas le calendrier national.
_GENERIC_EVENTS = re.compile(r"\bfetes?\b|\bferies?\b|\b(public|bank|national|religious) holidays?\b|\bupcoming (holidays?|feasts?)\b")
_PRIVATE_PARTY = re.compile(r"anniversaire|mariage|bapteme|soiree|birthday|wedding|\bparty\b")
# « L'Aïd » seul peut être la Korité ou la Tabaski : les deux sont montrées (mais pas « first aid »).
_AID = re.compile(r"(?<!first )\b(aid|eid)\b")
_STATUS = {
    "fr": ("date confirmée", "date estimée, à confirmer"),
    "en": ("confirmed date", "estimated date, to be confirmed"),
}

# Urgence que le sujet « urgences » de practical_facts ne déclenche pas (incendie, noyade, malaise…).
# Mots précis seulement : « saignant » (un steak), « étouffant » (la chaleur) ou « first aid » n'en sont pas.
_URGENCY_WORDS = re.compile(
    r"\bincendie|\bau feu\b|\bprend feu\b|\bnoyade\b|\bnoye(e|s|es)?\b|\bse noie\b|\bsaigne(nt|s)?\b|\bsaignements?\b|"
    r"\bhemorragi|\binconscient(e|s|es)?\b|crise cardiaque|\betouff(e|ee|es|er|ement)\b|\bempoisonn|\boverdose\b|"
    r"\bconvulsions?\b|\bon fire\b|\bhouse fire\b|\bdrown|\bbleeding\b|\bunconscious\b|heart attack|\bchoking\b|"
    r"\bpoison|\bseizure\b"
)

_NO_ANSWER = {
    "fr": ("L'assistant IA est momentanément indisponible, et je n'ai pas de réponse prête pour cette question dans la "
           "base vérifiée du site. Je préfère ne rien inventer."),
    "en": ("The AI assistant is temporarily unavailable, and I have no ready answer to this question in the site's "
           "verified knowledge base. I would rather not make anything up."),
}
_EMERGENCY_TITLE = {"fr": "En cas d'urgence", "en": "In an emergency (text in French)"}
_PATHS_TITLE = {"fr": "Ces pages du site peuvent déjà aider :", "en": "These pages of the site may already help:"}
# Pages qui existent sur le site (routes/places.py, emergency.py, events.py, services/trip_planner.py).
_PATHS = (
    ("teranga-ai.fr/lieux", "Lieux à visiter au Sénégal, avec histoire, carte et photos",
     "Places to visit in Senegal, with history, map and photos"),
    ("teranga-ai.fr/urgences", "Urgences : numéros utiles, lisible hors connexion",
     "Emergencies: useful numbers, readable offline"),
    ("teranga-ai.fr/calendrier-fetes-senegal", "Calendrier des fêtes et événements",
     "Calendar of holidays and events"),
    ("teranga-ai.fr/trip-planner", "Planificateur de voyage (itinéraire jour par jour), à réessayer quand l'assistant sera revenu",
     "Trip planner (day-by-day itinerary), to try again once the assistant is back"),
)


def _first_sentences(text: str, count: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    return " ".join(parts[:count]).strip()


def _place_text(place: dict) -> str:
    lines = [f"{place.get('name', '')} ({place.get('region', '')}) : {place.get('summary', '')}".strip()]
    history = _first_sentences(place.get("history", ""))
    if history and history not in lines[0]:
        lines.append(history)
    what = [item.strip() for item in str(place.get("what_to_see", "")).split(";") if item.strip()]
    if what:
        lines.append("À voir : " + ", ".join(what) + ".")
    if place.get("access"):
        lines.append("Comment y aller : " + str(place["access"]))
    return "\n".join(lines)


def _matched_dish(dishes, message: str) -> dict | None:
    folded = _fold(message)
    for dish in dishes or []:
        pattern = dish.get("_match") if isinstance(dish, dict) else None
        if pattern is not None and pattern.search(folded):
            return dish
    return None


def _section(title: str, lines) -> str:
    """Titre puis une puce par ligne (texte brut)."""
    return title + "\n" + "\n".join(f"• {line}" for line in lines)


def _practical_text(message: str, lang: str) -> str:
    """Repères pratiques vérifiés de la question, tels quels : titre de sujet puis puces.

    3 sujets au plus (les plus précis d'abord, comme matching_topics). Sous le plafond de caractères, on
    garde les premiers repères de chaque sujet, un tour après l'autre, et on n'en coupe aucun."""
    names = matching_topics(message, MAX_TOPICS)
    kept = {name: 0 for name in names}
    used = 0
    live = list(names)
    rank = 0
    while live:
        for name in tuple(live):
            facts = _FACTS[name]
            if rank >= len(facts) or (used and used + len(facts[rank]) > MAX_CHARS):
                live.remove(name)
                continue
            used += len(facts[rank])
            kept[name] = rank + 1
        rank += 1
    index = 1 if lang == "en" else 0
    return "\n\n".join(
        _section(_TITLES.get(name, _DEFAULT_TITLE)[index], _FACTS[name][: kept[name]]) for name in names if kept[name]
    )


def _event_line(event: dict, lang: str) -> str:
    when = french_date(event["start"]) + (f" au {french_date(event['end'])}" if event["end"] else "")
    status = _STATUS[lang][0 if event["confirmed"] else 1]
    return f"{event['name']} — {event['place']} : {when} ({status}). {event['tips']}"


def _events_text(message: str, lang: str, today: _dt.date | None) -> str:
    """Fêtes nommées dans la question, sinon les prochaines si elle parle des fêtes en général."""
    folded = _fold(message)
    upcoming = upcoming_events(today)
    chosen = [event for event in upcoming if _asked(event, folded)]
    if not chosen and _AID.search(folded):
        chosen = [event for event in upcoming if "Korité" in event["name"] or "Tabaski" in event["name"]]
    if not chosen and _GENERIC_EVENTS.search(folded) and not _PRIVATE_PARTY.search(folded):
        chosen = upcoming
    if not chosen:
        return ""
    return _section(_EVENTS_TITLE[1 if lang == "en" else 0], [_event_line(event, lang) for event in chosen[:MAX_EVENTS]])


def _is_urgent(message: str) -> bool:
    return "urgences" in matching_topics(message) or bool(_URGENCY_WORDS.search(_fold(message)))


def no_ready_answer(message: str, lang: str = "fr") -> str:
    """Quand rien ne correspond : le dire honnêtement, sans rien inventer, et indiquer les pages utiles.

    Les numéros d'urgence (repris de practical_facts) ne sont rappelés que si la question touche à une urgence."""
    lang = "en" if lang == "en" else "fr"
    index = 1 if lang == "en" else 0
    parts = [_NO_ANSWER[lang]]
    if _is_urgent(message):
        parts.append(_section(_EMERGENCY_TITLE[lang], _FACTS["urgences"][:2]))
    colon = " : " if lang == "fr" else ": "
    parts.append(_section(_PATHS_TITLE[lang], [f"{texts[index]}{colon}{path}" for path, *texts in _PATHS]))
    parts.append(_OUTRO[lang])
    return "\n\n".join(parts)


def knowledge_fallback(
    message: str, places, dishes=(), lang: str = "fr", *, always: bool = False, today: _dt.date | None = None
) -> str | None:
    """Réponse tirée de la base du site : lieu ou plat cité, fêtes, repères pratiques qui correspondent.

    Renvoie None quand rien ne correspond, sauf si `always` est vrai ou si la question touche à une
    urgence : le message honnête de `no_ready_answer` est alors renvoyé. `today` fixe la date de
    référence du calendrier (tests)."""
    lang = "en" if lang == "en" else "fr"
    found = mentioned_places(message, places or [], limit=1)
    by_id = {str(p.get("id")): p for p in places or [] if isinstance(p, dict)}
    body = ""
    if found:
        body = _place_text(by_id.get(found[0]["id"], found[0]))
    else:
        dish = _matched_dish(dishes, message)
        if dish:
            where = f" Où : {dish['where']}." if dish.get("where") else ""
            body = f"{dish.get('name')} : {dish.get('text')}{where}"
    parts = [part for part in (body, _events_text(message, lang, today), _practical_text(message, lang)) if part]
    if not parts:
        return no_ready_answer(message, lang) if always or _is_urgent(message) else None
    return f"{_INTRO[lang]}\n\n" + "\n\n".join(parts) + f"\n\n{_OUTRO[lang]}"
