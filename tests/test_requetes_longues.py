"""Requêtes longues plafonnées par processus : quelques réponses lentes ne bloquent plus tout le site.

Audit V3, P1-3 : Gunicorn tourne avec 2 processus de 4 fils ; 8 requêtes longues (chat, planificateur,
voix) occupaient tous les fils et /health passait de 0,01 s à 6,7 s. Chaque processus garde maintenant au
moins un fil pour les pages : au-delà de « fils - 1 » requêtes longues en cours, l'IA répond 503 tout de
suite (« très demandé »). Pas de limite par adresse IP : beaucoup de visiteurs au Sénégal partagent une
adresse, et le mode voix envoie jusqu'à 3 requêtes à la fois (réponse + 2 morceaux de voix). Aucun appel réseau.
"""

import json

import pytest

from latence_harness import B, app_module, completed, delta, finish, install_provider, post_chat
from services.long_requests import LONG_PATHS, LongRequestSlots, default_limit


def test_slots_stop_at_the_limit_and_come_back_once():
    slots = LongRequestSlots(2)
    first, second = slots.try_acquire(), slots.try_acquire()
    assert first and second and slots.try_acquire() is None
    first()
    first()  # une deuxième libération ne rend pas une place de plus
    assert slots.busy == 1
    assert slots.try_acquire() and slots.try_acquire() is None


def test_reset_ignores_releases_from_before():
    slots = LongRequestSlots(1)
    old = slots.try_acquire()
    slots.reset()
    fresh = slots.try_acquire()
    old()  # une place prise avant la remise à zéro ne libère pas la nouvelle
    assert fresh and slots.busy == 1


@pytest.mark.parametrize("threads,expected", [(None, 3), ("4", 3), ("8", 7), ("1", 1), ("abc", 3), ("99", 3)])
def test_default_limit_keeps_one_thread_for_pages(monkeypatch, threads, expected):
    if threads is None:
        monkeypatch.delenv("GUNICORN_THREADS", raising=False)
    else:
        monkeypatch.setenv("GUNICORN_THREADS", threads)
    assert default_limit() == expected


def test_long_routes_are_the_ai_routes():
    # /realtime-call (voix en temps réel, si REALTIME_VOICE_ENABLED=1) attend jusqu'à 25 s : relecture Codex sur #548.
    assert LONG_PATHS == frozenset({"/chat", "/api/trip-planner", "/api/practical-info", "/tts", "/stt", "/realtime-call"})


def test_when_full_the_ai_answers_503_at_once_and_pages_still_work(monkeypatch):
    install_provider(monkeypatch, events=[delta("Bonjour"), completed("Bonjour")])
    slots = app_module.LONG_SLOTS
    held = [slots.try_acquire() for _ in range(slots.limit)]
    assert all(held)
    response = post_chat("Que voir à Dakar ?")
    assert response.status_code == 503
    assert "très demandé" in response.get_json()["error"] and response.headers["Retry-After"]
    assert app_module.app.test_client().get("/health", base_url=B).status_code == 200
    for release in held:
        release()
    response = post_chat("Que voir à Dakar ?")
    finish(response)
    assert response.status_code == 200


def test_a_streamed_answer_holds_its_place_until_it_ends(monkeypatch):
    install_provider(monkeypatch, events=[delta("Bonjour"), completed("Bonjour")])
    slots = app_module.LONG_SLOTS
    response = post_chat("Que voir à Dakar ?")
    assert slots.busy == 1  # le flux n'est pas encore lu : la place reste prise
    body = finish(response)
    assert "Bonjour" in "".join(json.loads(line).get("d", "") for line in body.decode().splitlines() if line.strip())
    assert slots.busy == 0


def test_json_answers_and_refusals_give_their_place_back(monkeypatch):
    install_provider(monkeypatch, events=[delta("Bonjour"), completed("Bonjour")])
    finish(post_chat("Que voir à Dakar ?", json_mode=True))
    assert app_module.LONG_SLOTS.busy == 0
    refused = app_module.app.test_client().post("/chat", json={"message": "x"}, base_url=B)  # sans jeton CSRF
    assert refused.status_code in (400, 403) and app_module.LONG_SLOTS.busy == 0
