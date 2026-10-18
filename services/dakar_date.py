"""Date du jour à Dakar, donnée à l'IA pour situer « aujourd'hui », « ce week-end », « cette année ».

Calculée côté serveur dans le fuseau Africa/Dakar, quel que soit le fuseau de la machine.
Noms des jours et des mois écrits ici : le résultat ne dépend pas de la langue (locale) du serveur.
"""

import datetime as _dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def _dakar_zone():
    try:
        return ZoneInfo("Africa/Dakar")
    except ZoneInfoNotFoundError:
        # Base des fuseaux absente du serveur : le Sénégal est à GMT toute l'année (pas d'heure d'été).
        return _dt.timezone.utc


def _now_utc():
    """Horloge du serveur (remplacée par les tests pour figer la date)."""
    return _dt.datetime.now(_dt.timezone.utc)


def dakar_today(now=None):
    """Date du jour à Dakar ; `now` est un instant avec fuseau (par défaut, maintenant)."""
    return (now or _now_utc()).astimezone(_dakar_zone()).date()


def today_line(language="fr", today=None):
    """Ligne courte ajoutée aux instructions de l'IA ; en anglais si la conversation est en anglais."""
    day = today or dakar_today()
    if language == "en":
        return f"Today's date: {_DAYS[day.weekday()]}, {_MONTHS[day.month - 1]} {day.day}, {day.year} (Dakar time)."
    number = "1er" if day.day == 1 else str(day.day)
    return f"Date du jour : {_JOURS[day.weekday()]} {number} {_MOIS[day.month - 1]} {day.year} (heure de Dakar)."
