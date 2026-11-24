"""Météo en direct via Open-Meteo (gratuit, sans clé).

Pour une question météo sur un lieu connu du Sénégal, les prévisions réelles
sont ajoutées au contexte de l'IA : réponse plus rapide et plus juste qu'une
recherche web. En cas d'échec, l'appelant garde la recherche web.
"""

from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 15 * 60
# Relevé un peu ancien servi tout de suite pendant qu'un nouveau est demandé
# (l'heure du relevé figure dans le texte donné à l'IA).
STALE_SECONDS = 60 * 60
_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}
_LOCK = threading.Lock()
# Appels Open-Meteo en arrière-plan : une réponse lente n'immobilise pas le chat.
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="meteo")
_PENDING: dict[tuple[float, float], Future] = {}

# Codes météo WMO utilisés par Open-Meteo.
_CODES = {
    0: ("ciel dégagé", "clear sky"), 1: ("plutôt dégagé", "mostly clear"),
    2: ("partiellement nuageux", "partly cloudy"), 3: ("couvert", "overcast"),
    45: ("brouillard", "fog"), 48: ("brouillard givrant", "freezing fog"),
    51: ("bruine légère", "light drizzle"), 53: ("bruine", "drizzle"), 55: ("bruine forte", "heavy drizzle"),
    61: ("pluie faible", "light rain"), 63: ("pluie", "rain"), 65: ("forte pluie", "heavy rain"),
    80: ("averses", "showers"), 81: ("averses", "showers"), 82: ("fortes averses", "heavy showers"),
    95: ("orages", "thunderstorms"), 96: ("orages avec grêle", "thunderstorms with hail"),
    99: ("violents orages", "severe thunderstorms"),
}


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").strip()


def build_locations(region_coords: dict, places: list) -> dict[str, tuple[str, float, float]]:
    """{nom normalisé: (nom affiché, latitude, longitude)} pour régions et lieux."""
    locations = {}
    for name, (lat, lon) in (region_coords or {}).items():
        locations[_normalize(name)] = (name, float(lat), float(lon))
    for place in places or []:
        try:
            lat, lon = float(place["latitude"]), float(place["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        name = str(place.get("name") or "").strip()
        if name:
            locations.setdefault(_normalize(name), (name, lat, lon))
    return locations


def resolve_location(locations: dict, location: object, message: object = ""):
    key = _normalize(location)
    if key in locations:
        return locations[key]
    text = _normalize(message)
    # Le nom le plus long d'abord : « saint-louis » avant « louis ».
    for name in sorted(locations, key=len, reverse=True):
        if len(name) >= 4 and name in text:
            return locations[name]
    return None


def fetch_forecast(lat: float, lon: float, *, opener=None, now=None) -> dict:
    key = (round(lat, 2), round(lon, 2))
    now = time.monotonic() if now is None else now
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < CACHE_SECONDS:
            return cached[1]
    params = {
        "latitude": key[0], "longitude": key[1], "timezone": "Africa/Dakar", "forecast_days": 4,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
    }
    request = Request(API + "?" + urlencode(params), headers={"User-Agent": "TerangaAI/1.0 (weather)"})
    with (opener or urlopen)(request, timeout=4) as response:
        data = json.loads(response.read().decode("utf-8"))
    with _LOCK:
        if len(_CACHE) > 64:
            _CACHE.clear()
        _CACHE[key] = (now, data)
    return data


def _refresh(lat: float, lon: float, opener=None) -> Future:
    """Appel Open-Meteo en arrière-plan ; un seul à la fois par lieu."""
    key = (round(lat, 2), round(lon, 2))
    with _LOCK:
        pending = _PENDING.get(key)
        if pending is not None and not pending.done():
            return pending
        future = _EXECUTOR.submit(fetch_forecast, lat, lon, opener=opener)
        _PENDING[key] = future
    return future


def forecast_within(lat: float, lon: float, budget: float, *, opener=None, now=None) -> dict | None:
    """Prévisions sans attendre plus de ``budget`` secondes ; None si Open-Meteo est trop lent.

    Un relevé récent sert directement. Un relevé de moins d'une heure sert aussi, et un
    nouveau est demandé en arrière-plan. Sinon l'appel attend au plus ``budget`` : au-delà,
    il continue seul et remplit le cache pour la question suivante.
    """
    key = (round(lat, 2), round(lon, 2))
    now = time.monotonic() if now is None else now
    with _LOCK:
        cached = _CACHE.get(key)
    age = now - cached[0] if cached else None
    if age is not None and age < CACHE_SECONDS:
        return cached[1]
    future = _refresh(lat, lon, opener)
    if age is not None and age < STALE_SECONDS and _same_day_in_dakar(cached[1]):
        return cached[1]
    try:
        return future.result(timeout=budget)
    except FutureTimeout:
        if future.done():
            raise  # TimeoutError levé par l'appel lui-même : service indisponible, pas lent
        return None


def _same_day_in_dakar(data: dict) -> bool:
    """Le relevé date-t-il d'aujourd'hui à Dakar (UTC+0) ? Sinon « Aujourd'hui » serait la veille."""
    observed = str((data.get("current") or {}).get("time") or "")[:10]
    return observed == datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _describe(code, language):
    pair = _CODES.get(int(code)) if code is not None else None
    return (pair[1] if language == "en" else pair[0]) if pair else ("variable" if language == "en" else "temps variable")


def format_forecast(place: str, data: dict, language: str = "fr") -> str:
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    en = language == "en"
    stamp = str(current.get("time") or "")
    try:
        stamp = datetime.fromisoformat(stamp).strftime("%d/%m %H:%M")
    except ValueError:
        pass
    lines = [
        ("LIVE WEATHER (Open-Meteo, observed " if en else "MÉTÉO EN DIRECT (Open-Meteo, relevée le ")
        + stamp + (" Dakar time) for " if en else " heure de Dakar) pour ") + place + " :",
        ("Now: " if en else "Maintenant : ")
        + f"{current.get('temperature_2m')} °C"
        + (f" (feels like {current.get('apparent_temperature')} °C)" if en else f" (ressenti {current.get('apparent_temperature')} °C)")
        + f", {_describe(current.get('weather_code'), language)}"
        + (f", wind {current.get('wind_speed_10m')} km/h" if en else f", vent {current.get('wind_speed_10m')} km/h")
        + (f", humidity {current.get('relative_humidity_2m')} %." if en else f", humidité {current.get('relative_humidity_2m')} %."),
    ]
    labels = ("Today", "Tomorrow") if en else ("Aujourd'hui", "Demain")
    for index, day in enumerate(daily.get("time") or []):
        try:
            label = labels[index] if index < 2 else datetime.fromisoformat(day).strftime("%d/%m")
            lines.append(
                f"- {label} : {_describe(daily['weather_code'][index], language)}, "
                f"{daily['temperature_2m_min'][index]}–{daily['temperature_2m_max'][index]} °C, "
                + (f"rain risk {daily['precipitation_probability_max'][index]} %, " if en else f"risque de pluie {daily['precipitation_probability_max'][index]} %, ")
                + (f"wind up to {daily['wind_speed_10m_max'][index]} km/h" if en else f"vent jusqu'à {daily['wind_speed_10m_max'][index]} km/h")
            )
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    lines.append(
        "Answer from these figures, mention Open-Meteo, and refer to ANACIM for official alerts."
        if en else
        "Réponds à partir de ces chiffres, cite Open-Meteo, et renvoie vers l'ANACIM pour les alertes officielles."
    )
    return "\n".join(lines)


# « à Paris », « in London », « pour Abidjan » : un lieu est nommé (mais inconnu de la base du Sénégal).
_PLACE_AFTER_PREPOSITION = re.compile(
    r"\b(?:a|au|aux|en|in|at|pour|for|near|vers)\s+"
    r"(?!(?:le|la|les|l|ce|cet|cette|ces|aujourd|demain|maintenant|this|the|today|tomorrow|tonight|now|next|midi|minuit)\b|\d)"
    r"([a-z][a-z'-]{2,})"
)


def _names_unknown_place(message: str) -> bool:
    return bool(_PLACE_AFTER_PREPOSITION.search(_normalize(message)))


def live_weather_context(
    locations: dict, intent_context: dict, message: str, language: str = "fr", *, opener=None, logger=None,
    budget: float | None = None,
):
    """Texte météo prêt pour le prompt, ou None (lieu inconnu, service indisponible ou trop lent).

    Avec ``budget`` (secondes), l'attente d'Open-Meteo est bornée (voir ``forecast_within``).
    """
    if (intent_context or {}).get("intent") != "weather":
        return None
    found = resolve_location(locations, (intent_context or {}).get("location"), message)
    if found is None and _names_unknown_place(message):
        return None  # « Météo à Paris » : la recherche web répond, pas les prévisions de Dakar
    if found is None:
        found = locations.get("dakar")  # « Quel temps fait-il ? » : Dakar par défaut
    if found is None:
        return None
    name, lat, lon = found
    try:
        if budget is None:
            data = fetch_forecast(lat, lon, opener=opener)
        else:
            data = forecast_within(lat, lon, budget, opener=opener)
            if data is None:
                if logger is not None:
                    logger.info("open-meteo trop lent: recherche web")
                return None
        return format_forecast(name, data, language)
    except Exception as exc:  # noqa: BLE001 - la recherche web prend le relais
        if logger is not None:
            logger.warning("open-meteo indisponible: %s", type(exc).__name__)
        return None
