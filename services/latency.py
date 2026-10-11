"""Mesure de latence : UNE ligne de journal par requête (chat, /stt, /tts), sans aucune donnée personnelle.

Rien n'est optimisé ici : ce module sert à MESURER où le temps passe avant de chercher à aller plus vite.

Format (stable, sur UNE seule ligne, des paires ``clé=valeur`` séparées par une espace ; « - » = sans objet) :

    latence route=chat total_ms=2310.4 contexte_ms=12.8 recherche_ms=- premier_mot_ms=1480.2 fournisseur_ms=1410.9 cache=non modele=nom-du-modele mode=flux statut=ok
    latence route=stt total_ms=950.1 fournisseur_ms=902.6 modele=gpt-4o-transcribe statut=ok

Confidentialité : la ligne n'est construite QUE à partir de nombres (millisecondes) et d'étiquettes fixes
(route, oui/non, mode, statut) ou validées (nom de modèle, lu dans la configuration, jamais dans la requête).
Aucune valeur libre n'est acceptée : tout ce qui n'a pas la forme attendue devient « - » ou « autre ». Ni la
question, ni la réponse, ni l'adresse IP, ni l'identifiant du visiteur, ni une clé ne peuvent donc y figurer.

Le journal Flask (``app.logger``) n'affiche PAS le niveau INFO sous Gunicorn (niveau WARNING par défaut,
aucune configuration dans le projet) : un simple ``app.logger.info`` ne sortirait jamais dans les journaux
de Render. Ces lignes passent par un journal dédié (``teranga.latence``), réglé sur INFO, qui écrit sur la
sortie standard.
"""
from __future__ import annotations

import logging
import math
import re
import sys
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from typing import Any

LOGGER_NAME = "teranga.latence"
LINE_PREFIX = "latence"
PAYLOAD_KEY = "latency_model"  # clé privée de la requête du chat : lue par routes/chat.py, jamais envoyée au client

# Champs de chaque route, dans l'ordre d'écriture. Une clé absente de la requête s'écrit « - ».
CHAT_FIELDS = (
    "total_ms", "contexte_ms", "recherche_ms", "premier_mot_ms", "fournisseur_ms", "cache", "modele", "mode", "statut",
)
VOICE_FIELDS = ("total_ms", "fournisseur_ms", "modele", "statut")
FIELDS_BY_ROUTE: dict[str, tuple[str, ...]] = {"chat": CHAT_FIELDS, "stt": VOICE_FIELDS, "tts": VOICE_FIELDS}

MODES = frozenset({"flux", "json"})
# ok : réponse normale · secours : réponse de repli (IA en panne) · erreur : échec côté serveur ou fournisseur ·
# abandon : le visiteur a fermé la connexion avant la fin · refuse : limite de débit (429) · invalide : requête refusée (4xx).
STATUSES = frozenset({"ok", "secours", "erreur", "abandon", "refuse", "invalide"})

# Nom de modèle : lettres, chiffres et « . _ : - », 48 caractères au plus. Ces noms viennent de la configuration
# (OPENAI_MODEL, ANTHROPIC_MODEL, STT_MODEL…), jamais de la question ; tout autre texte devient « autre ».
_MODEL_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,47}")

_SETUP_LOCK = threading.Lock()
_ready = False


class _StdoutHandler(logging.StreamHandler):
    """Écrit sur la sortie standard courante (relue à chaque ligne) : Render la capture, et les tests aussi."""

    def __init__(self) -> None:
        logging.Handler.__init__(self)

    @property
    def stream(self):  # type: ignore[override]
        return sys.stdout


def get_logger() -> logging.Logger:
    """Journal dédié aux lignes de latence, réglé une fois sur INFO (voir l'explication en tête de fichier)."""
    global _ready
    log = logging.getLogger(LOGGER_NAME)
    if not _ready:
        with _SETUP_LOCK:
            if not _ready:
                log.setLevel(logging.INFO)
                log.propagate = False  # une seule sortie, même si quelqu'un configure plus tard le journal racine
                handler = _StdoutHandler()
                handler.setFormatter(logging.Formatter("%(message)s"))
                log.addHandler(handler)
                _ready = True
    return log


def _ms(value: Any) -> str:
    """Millisecondes avec une décimale ; « - » si la valeur est absente ou n'est pas un nombre fini."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "-"
    if not math.isfinite(value):
        return "-"
    return f"{max(0.0, float(value)):.1f}"


def _yes_no(value: Any) -> str:
    return {True: "oui", False: "non"}.get(value, "-") if isinstance(value, bool) else "-"


def _model(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return value if isinstance(value, str) and _MODEL_LABEL.fullmatch(value) else "autre"


def _mode(value: Any) -> str:
    return value if isinstance(value, str) and value in MODES else "-"


def _status(value: Any) -> str:
    return value if isinstance(value, str) and value in STATUSES else "erreur"


def _render(key: str, value: Any) -> str:
    if key.endswith("_ms"):
        return _ms(value)
    return {"cache": _yes_no, "modele": _model, "mode": _mode, "statut": _status}[key](value)


def format_line(route: str, values: Mapping[str, Any]) -> str:
    """Ligne de journal à partir de valeurs brutes. Les clés inconnues sont ignorées, les valeurs inattendues neutralisées."""
    if route not in FIELDS_BY_ROUTE:
        return f"{LINE_PREFIX} route=autre total_ms={_ms(values.get('total_ms'))} statut={_status(values.get('statut'))}"
    pairs = " ".join(f"{key}={_render(key, values.get(key))}" for key in FIELDS_BY_ROUTE[route])
    return f"{LINE_PREFIX} route={route} {pairs}"


def note_model(payload: Any, name: Any) -> None:
    """Retient dans la requête le modèle réellement appelé, pour la ligne de latence (le nom vient de la configuration)."""
    if isinstance(payload, dict):
        payload[PAYLOAD_KEY] = name


def status_from_http(code: Any) -> str:
    """Statut déduit du code HTTP quand la route n'en a pas fixé un elle-même."""
    try:
        number = int(code)
    except (TypeError, ValueError):
        return "erreur"
    if number < 400:
        return "ok"
    if number == 429:
        return "refuse"
    return "invalide" if number < 500 else "erreur"


class LatencyTrace:
    """Chronomètres d'UNE requête ; ``emit`` écrit la ligne de journal, une seule fois, sans jamais lever d'erreur.

    Utilisation dans une route : ``return LatencyTrace("chat").run(app, corps)`` où ``corps(trace)`` est la route
    d'origine. La ligne part à la fermeture de la réponse (fin du flux, ou connexion fermée par le visiteur).
    """

    def __init__(self, route: str, *, clock: Callable[[], float] = time.perf_counter) -> None:
        self.route = route
        self._clock = clock
        self._t0 = clock()
        self._starts: dict[str, float] = {}
        self._stages: dict[str, float] = {}
        self._first_word_ms: float | None = None
        self._emitted = False
        self._http_status: int | None = None
        self._streamed = False
        # Renseignés par la route.
        self.cache: bool | None = None
        self.model: str | None = None
        self.mode: str | None = None
        self.status: str | None = None

    # -- chronomètres ------------------------------------------------------------------------------------

    def elapsed_ms(self) -> float:
        return (self._clock() - self._t0) * 1000

    def begin(self, name: str) -> None:
        """Démarre l'étape ``name`` (sans effet si elle tourne déjà)."""
        self._starts.setdefault(name, self._clock())

    def end(self, name: str) -> None:
        """Arrête l'étape ``name`` et ajoute sa durée ; sans effet si elle n'a pas démarré (ou déjà été arrêtée)."""
        started = self._starts.pop(name, None)
        if started is not None:
            self._stages[name] = self._stages.get(name, 0.0) + (self._clock() - started) * 1000

    @contextmanager
    def stage(self, name: str):
        """Mesure le bloc, même s'il lève une exception (qui continue de se propager)."""
        self.begin(name)
        try:
            yield
        finally:
            self.end(name)

    def first_word(self) -> None:
        """À appeler juste avant d'envoyer au client le premier texte : seul le premier appel compte.

        Il arrête aussi le chronomètre « fournisseur » (attente du fournisseur jusqu'au premier mot)."""
        if self._first_word_ms is None:
            self._first_word_ms = self.elapsed_ms()
            self.end("fournisseur")

    # -- émission ----------------------------------------------------------------------------------------

    def follow(self, response):
        """Fait partir la ligne quand la réponse est fermée (après le dernier octet d'un flux)."""
        self._http_status = getattr(response, "status_code", None)
        self._streamed = bool(getattr(response, "is_streamed", False))
        response.call_on_close(self.emit)
        return response

    def run(self, app, handler: Callable[["LatencyTrace"], Any]):
        """Exécute la route ``handler(trace)`` et suit sa réponse. Même résultat que sans mesure.

        Une exception de la route est relancée telle quelle (Flask répond alors 500 ou le code de l'exception HTTP)."""
        try:
            result = handler(self)
        except Exception as exc:
            self.status = self.status or status_from_http(getattr(exc, "code", None) or 500)
            self.emit()
            raise
        return self.follow(app.make_response(result))

    def _final_status(self) -> str:
        if self.status is not None:
            return self.status
        if self._streamed:
            return "abandon"  # le flux a été fermé avant d'avoir signalé sa fin
        return status_from_http(self._http_status if self._http_status is not None else 500)

    def values(self) -> dict[str, Any]:
        """Valeurs brutes de la ligne (les étapes absentes valent None, donc « - »)."""
        return {
            "total_ms": self.elapsed_ms(),
            "contexte_ms": self._stages.get("contexte"),
            "recherche_ms": self._stages.get("recherche"),
            "premier_mot_ms": self._first_word_ms,
            "fournisseur_ms": self._stages.get("fournisseur"),
            "cache": self.cache,
            "modele": self.model,
            "mode": self.mode,
            "statut": self._final_status(),
        }

    def emit(self) -> None:
        """Écrit la ligne (une seule fois). Une mesure ne doit jamais gêner la réponse : toute erreur est avalée."""
        if self._emitted:
            return
        self._emitted = True
        try:
            get_logger().info("%s", format_line(self.route, self.values()))
        except Exception:  # noqa: BLE001 - la mesure est facultative
            pass
