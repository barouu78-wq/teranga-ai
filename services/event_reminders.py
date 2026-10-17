"""Rappels des fêtes : fichiers calendrier iCalendar (RFC 5545).

Gratuit et sans compte : le téléphone (Google Agenda, Calendrier d'Apple, Outlook)
garde l'événement et sonne lui-même 7 jours puis 1 jour avant. Aucune donnée
personnelle, aucune notification envoyée par le serveur. Les dates viennent de
services/events.py ; une date lunaire non confirmée est dite « estimée » dans le
titre et la description, puisque le fichier enregistré ne se met pas à jour.
"""

from __future__ import annotations

import datetime as _dt
import re

from services.events import upcoming_events
from services.text import fold_text

_PRODID = "-//Teranga AI//Calendrier des fetes du Senegal//FR"
# Relatifs à minuit le jour de la fête : 9 h une semaine avant, puis 9 h la veille.
_ALARMS = (("P6DT15H", "dans une semaine"), ("PT15H", "demain"))
_ESTIMATE_NOTE = (
    "Date estimée, à vérifier : les fêtes musulmanes suivent le calendrier lunaire et la date est "
    "confirmée quelques jours avant par la commission nationale du croissant lunaire ou les familles religieuses."
)


def event_slug(event: dict) -> str:
    """« Tabaski (Aïd el-Kébir) » de 2027 → « tabaski-aid-el-kebir-2027 ».

    Nom et année seulement : quand une date estimée est confirmée (Tabaski du 17 au 16 mai),
    le lien reste valable et l'agenda remplace l'événement (même UID) au lieu de le doubler."""
    words = re.sub(r"[^a-z0-9]+", "-", fold_text(event["name"])).strip("-")
    return f"{words}-{event['start'].year}"


def find_event(slug: str, today: _dt.date | None = None) -> dict | None:
    """Événement en cours ou à venir de ce slug, sinon None (passé ou inconnu)."""
    for event in upcoming_events(today):
        if event_slug(event) == slug:
            return event
    return None


def _escape(text: object) -> str:
    return (
        str(text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        .replace("\r\n", "\\n").replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Lignes de 75 octets au plus, suite précédée d'une espace (RFC 5545, 3.1)."""
    parts, current, size = [], "", 0
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > 75:
            parts.append(current)
            current, size = " ", 1
        current += char
        size += width
    parts.append(current)
    return "\r\n".join(parts)


def _vevent(event: dict, site_url: str, stamp: str) -> list[str]:
    estimated = not event["confirmed"]
    title = event["name"] + (" (date estimée)" if estimated else "")
    end = (event["end"] or event["start"]) + _dt.timedelta(days=1)  # DTEND exclusif
    page = site_url.rstrip("/") + "/calendrier-fetes-senegal"
    description = event["tips"] + ("\n\n" + _ESTIMATE_NOTE if estimated else "") + "\n\nTeranga AI : " + page
    lines = [
        "BEGIN:VEVENT",
        f"UID:{event_slug(event)}@teranga-ai.fr",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{event['start']:%Y%m%d}",
        f"DTEND;VALUE=DATE:{end:%Y%m%d}",
        f"SUMMARY:{_escape(title)}",
        f"LOCATION:{_escape(event['place'] + ', Sénégal')}",
        f"DESCRIPTION:{_escape(description)}",
        f"URL:{page}",
        "TRANSP:TRANSPARENT",
    ]
    for trigger, when in _ALARMS:
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"TRIGGER:-{trigger}",
            f"DESCRIPTION:{_escape(title + ' : ' + when)}",
            "END:VALARM",
        ]
    lines.append("END:VEVENT")
    return lines


def calendar_ics(events: list[dict], site_url: str, now: _dt.datetime | None = None) -> str:
    """Fichier .ics complet pour ces événements."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    stamp = now.astimezone(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Fêtes au Sénégal (Teranga AI)",
    ]
    for event in events:
        lines += _vevent(event, site_url, stamp)
    lines.append("END:VCALENDAR")
    return "".join(_fold(line) + "\r\n" for line in lines)
