"""Requêtes longues plafonnées par processus : quelques réponses lentes ne bloquent plus tout le site.

Audit V3, P1-3 : Gunicorn tourne avec 2 processus de 4 fils (gunicorn.conf.py). Huit requêtes longues
(chat, planificateur, voix) occupaient tous les fils : les pages et /health attendaient leur tour. Chaque
processus accepte maintenant au plus « fils - 1 » requêtes longues à la fois ; au-delà, réponse 503 immédiate.
Un fil reste toujours libre pour les pages.

Pas de limite par adresse IP : beaucoup de visiteurs au Sénégal partagent une adresse (réseaux mobiles), et le
mode voix envoie jusqu'à 3 requêtes à la fois. Les limites de débit par visiteur existent déjà (app.py).
"""

from __future__ import annotations

import os
import threading

from flask import g, jsonify, request

# /realtime-call n'existe que si REALTIME_VOICE_ENABLED=1 ; il attend la réponse d'OpenAI jusqu'à 25 s.
LONG_PATHS = frozenset({"/chat", "/api/trip-planner", "/api/practical-info", "/tts", "/stt", "/realtime-call"})
BUSY_MESSAGE = "Teranga est très demandé en ce moment. Réessaie dans quelques secondes."


def default_limit() -> int:
    """« fils - 1 », d'après GUNICORN_THREADS lu comme gunicorn.conf.py (défaut 4, de 1 à 16), au moins 1."""
    try:
        threads = int(os.environ.get("GUNICORN_THREADS", ""))
    except ValueError:
        threads = 4
    if not 1 <= threads <= 16:
        threads = 4
    return max(1, threads - 1)


class LongRequestSlots:
    def __init__(self, limit: int):
        self.limit = limit
        self.busy = 0
        self._generation = 0
        self._lock = threading.Lock()

    def try_acquire(self):
        """Une place libre : renvoie la fonction qui la rend (sans effet après le premier appel) ; sinon None."""
        with self._lock:
            if self.busy >= self.limit:
                return None
            self.busy += 1
            generation = self._generation
        released = False

        def release():
            nonlocal released
            with self._lock:
                if released or generation != self._generation:
                    return
                released = True
                self.busy -= 1

        return release

    def reset(self) -> None:
        """Toutes les places libres (tests) ; les places prises avant ne seront plus rendues."""
        with self._lock:
            self.busy = 0
            self._generation += 1


def install_long_request_limit(app, slots: LongRequestSlots, logger) -> None:
    @app.before_request
    def _take_long_slot():
        if request.method != "POST" or request.path not in LONG_PATHS:
            return None
        release = slots.try_acquire()
        if release is None:
            logger.warning("requetes_longues_pleines chemin=%s places=%s", request.path, slots.limit)
            return jsonify({"error": BUSY_MESSAGE}), 503, {"Retry-After": "5"}
        g.long_slot_release = release
        return None

    @app.after_request
    def _give_long_slot_back(response):
        release = g.pop("long_slot_release", None)
        if release is None:
            return response
        if not response.is_streamed:
            release()  # tout le travail est fait : la réponse est déjà prête
            return response
        body = response.response

        def held_until_the_end():
            try:
                yield from body
            finally:
                release()

        # Un flux garde sa place jusqu'à la fin de la lecture ; s'il n'est jamais lu, la fermeture la rend.
        response.response = held_until_the_end()
        response.call_on_close(release)
        return response

    @app.teardown_request
    def _long_slot_safety(_exc):
        release = g.pop("long_slot_release", None)
        if release is not None:
            release()
