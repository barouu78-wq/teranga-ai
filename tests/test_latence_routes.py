"""Lignes de latence écrites par /chat, /stt et /tts (vraie application, faux fournisseur, aucun appel réseau).

Chaque requête laisse UNE ligne `latence route=… clé=valeur …`. Les durées ne sont vérifiées que par des bornes
basses (un `sleep` ne rend jamais la main trop tôt) et par leur ordre, jamais par des valeurs exactes.
"""

import os

import pytest

import latence_harness as h
from latence_harness import completed, delta, failed, finish, full, post_chat

from services.model_params import openai_complex_model, openai_model

QUESTION = "Parle-moi de la culture sérère."  # ni recherche web ni planificateur : la réponse est mise en cache
WEB_QUESTION = "Quel est le prix actuel du ticket de TER à Dakar ?"  # question qui vieillit vite : recherche web
TEXT = "Prends un car depuis la gare routière de Pompiers, c'est le plus simple."
STREAM = [delta("Prends un car depuis "), delta("la gare routière de Pompiers, "), delta("c'est le plus simple."), completed(TEXT)]
MODELS = {openai_model(), openai_complex_model()}


@pytest.fixture
def lines():
    handler = h.capture_lines()
    yield handler.lines
    h.release_lines(handler)


def one(lines):
    assert len(lines) == 1, lines
    return h.fields(lines[0])


def number(value):
    assert value != "-" and float(value) >= 0, value
    return float(value)


# --- /chat en flux ----------------------------------------------------------------------------------------


def test_a_streamed_answer_leaves_one_line_with_every_stage(monkeypatch, lines):
    provider = h.install_provider(monkeypatch, events=STREAM, pause=0.05, first_pause=0.05)
    finish(post_chat(QUESTION))
    f = one(lines)
    assert f["route"] == "chat" and f["mode"] == "flux" and f["cache"] == "non" and f["web"] == "non" and f["statut"] == "ok"
    assert f["modele"] in MODELS
    assert f["recherche_ms"] == "-"  # pas de recherche externe pour cette question
    assert number(f["contexte_ms"]) >= 0
    assert number(f["fournisseur_ms"]) >= 95  # 0,05 s de connexion + 0,05 s avant le premier mot
    assert number(f["fournisseur_ms"]) <= number(f["premier_mot_ms"]) <= number(f["total_ms"])
    assert number(f["contexte_ms"]) <= number(f["premier_mot_ms"])
    assert provider.calls == [True]


def test_the_same_question_again_is_a_cache_hit_without_a_provider_call(monkeypatch, lines):
    provider = h.install_provider(monkeypatch, events=STREAM)
    finish(post_chat(QUESTION))
    finish(post_chat(QUESTION))
    assert len(lines) == 2
    first, second = h.fields(lines[0]), h.fields(lines[1])
    assert first["cache"] == "non" and second["cache"] == "oui"
    assert second["fournisseur_ms"] == "-" and second["modele"] == "-"  # aucun modèle appelé
    assert number(second["premier_mot_ms"]) <= number(second["total_ms"]) and second["statut"] == "ok"
    assert provider.calls == [True]


def test_json_mode_has_no_first_word_and_counts_the_whole_provider_call(monkeypatch, lines):
    h.install_provider(monkeypatch, full_reply=full(TEXT), pause=0.05)
    finish(post_chat(QUESTION, json_mode=True))
    f = one(lines)
    assert f["mode"] == "json" and f["premier_mot_ms"] == "-" and f["cache"] == "non" and f["statut"] == "ok"
    assert f["modele"] in MODELS and number(f["fournisseur_ms"]) >= 45
    finish(post_chat(QUESTION, json_mode=True))
    assert h.fields(lines[1])["cache"] == "oui"


def test_a_provider_failure_answered_from_the_knowledge_base_is_a_secours(monkeypatch, lines):
    h.install_provider(monkeypatch, error="fournisseur en panne")
    finish(post_chat("Que visiter à Gorée en famille ?"))
    finish(post_chat("Que visiter à Saly en famille ?", json_mode=True))
    streamed, json_mode = (h.fields(line) for line in lines)
    assert streamed["statut"] == "secours" and number(streamed["premier_mot_ms"]) > 0 and streamed["modele"] in MODELS
    assert json_mode["statut"] == "secours" and json_mode["mode"] == "json"


def test_a_response_failed_event_before_any_word_is_a_secours(monkeypatch, lines):
    h.install_provider(monkeypatch, events=[failed()])
    finish(post_chat("Quelle est la meilleure saison pour Lompoul ?"))
    assert one(lines)["statut"] == "secours"


def test_an_empty_stream_retried_without_streaming_stays_ok(monkeypatch, lines):
    provider = h.install_provider(monkeypatch, events=[], full_reply=full("Réponse complète donnée par le second appel."))
    finish(post_chat("Où manger un thiéboudienne à Dakar ?"))
    f = one(lines)
    assert f["statut"] == "ok" and number(f["premier_mot_ms"]) > 0
    assert provider.calls == [True, False]


def test_nothing_from_the_model_at_all_is_a_secours(monkeypatch, lines):
    h.install_provider(monkeypatch, events=[], full_reply=full(""))
    finish(post_chat("Une question sans réponse du modèle ?"))
    assert one(lines)["statut"] == "secours"


def test_a_stream_closed_by_the_visitor_is_an_abandon(monkeypatch, lines):
    h.install_provider(monkeypatch, events=STREAM)
    response = post_chat("Quel car prendre pour aller de Dakar à Thiès ?")
    assert next(response.response)  # le visiteur reçoit le premier morceau…
    response.close()  # …puis ferme la connexion
    f = one(lines)
    assert f["statut"] == "abandon" and f["fournisseur_ms"] != "-"


def test_a_request_refused_by_the_rate_limit_is_labelled_refuse(monkeypatch, lines):
    h.install_provider(monkeypatch, events=STREAM)
    ip = h.next_ip()
    for _ in range(h.app_module.RATE_LIMIT + 2):
        finish(post_chat("Salut", ip=ip))
    statuts = [h.fields(line)["statut"] for line in lines]
    assert statuts[0] == "ok" and statuts[-1] == "refuse"
    refused = h.fields(lines[-1])
    assert refused["contexte_ms"] == "-" and refused["premier_mot_ms"] == "-"  # refusée avant tout travail


def test_an_empty_message_is_labelled_invalide_after_the_context_step(monkeypatch, lines):
    h.install_provider(monkeypatch, events=STREAM)
    finish(post_chat("   "))
    f = one(lines)
    assert f["statut"] == "invalide" and number(f["contexte_ms"]) >= 0 and f["fournisseur_ms"] == "-"


def test_every_request_leaves_exactly_one_line(monkeypatch, lines):
    h.install_provider(monkeypatch, events=STREAM)
    for question in ("Que faire à Dakar ?", "Que faire à Thiès ?", "Que faire à Saly ?"):
        finish(post_chat(question))
    assert len(lines) == 3


# --- Recherche externe ------------------------------------------------------------------------------------


def test_the_external_search_is_timed_only_when_it_runs(monkeypatch, lines):
    from services import external_research

    def slow_engine(name, query):
        import time

        time.sleep(0.06)
        return {"provider": name, "context": "Résultat de recherche de test.", "sources": [{"title": "Test", "url": "https://exemple.sn/test"}]}

    monkeypatch.setenv("TAVILY_API_KEY", "cle-de-test-factice")
    monkeypatch.setattr(external_research, "_engine_context", slow_engine)
    h.install_provider(monkeypatch, events=STREAM)
    finish(post_chat(WEB_QUESTION))
    with_search = one(lines)
    assert number(with_search["recherche_ms"]) >= 55 and with_search["statut"] == "ok"
    assert number(with_search["recherche_ms"]) <= number(with_search["premier_mot_ms"])
    assert with_search["web"] == "non"  # le contexte trouvé remplace l'outil de recherche du fournisseur
    finish(post_chat(QUESTION))
    without = h.fields(lines[1])
    assert without["recherche_ms"] == "-" and without["web"] == "non"


def test_a_web_question_without_a_search_connector_is_flagged_web_oui(monkeypatch, lines):
    for name in ("TAVILY_API_KEY", "EXA_API_KEY", "FIRECRAWL_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    h.install_provider(monkeypatch, events=STREAM)
    finish(post_chat(WEB_QUESTION))
    f = one(lines)
    # Sans clé de recherche, c'est l'outil web du fournisseur qui travaille : son temps est dans fournisseur_ms.
    assert f["web"] == "oui" and f["cache"] == "non" and f["statut"] == "ok"


# --- Voix -------------------------------------------------------------------------------------------------


def test_stt_line_measures_the_provider_call(monkeypatch, lines):
    response = h.post_stt(monkeypatch=monkeypatch)
    assert response.status_code == 200 and response.get_json() == {"text": "bonjour"}
    response.close()
    f = one(lines)
    assert f["route"] == "stt" and f["statut"] == "ok"
    assert f["modele"] == os.getenv("STT_MODEL", "gpt-4o-transcribe")
    assert number(f["fournisseur_ms"]) <= number(f["total_ms"])
    assert set(f) == {"route", "total_ms", "fournisseur_ms", "modele", "statut"}


def test_stt_failure_is_an_erreur_but_the_provider_time_is_kept(monkeypatch, lines):
    response = h.post_stt(error="stt en panne", monkeypatch=monkeypatch)
    assert response.status_code == 500
    response.close()
    f = one(lines)
    assert f["statut"] == "erreur" and f["fournisseur_ms"] != "-"


def test_stt_without_audio_never_reaches_the_provider(monkeypatch, lines):
    response = h.post_stt(audio=None, monkeypatch=monkeypatch)
    assert response.status_code == 400
    response.close()
    f = one(lines)
    assert f["statut"] == "invalide" and f["fournisseur_ms"] == "-" and f["modele"] == "-"


def test_tts_line_measures_the_provider_call(monkeypatch, lines):
    response = h.post_tts("Bonjour Dakar", monkeypatch=monkeypatch)
    assert response.status_code == 200 and response.data == b"".join(h.fake_speech.FAKE_MP3)
    response.close()
    f = one(lines)
    assert f["route"] == "tts" and f["statut"] == "ok" and f["modele"] == "gpt-4o-mini-tts"
    # premier_mot_ms : premier octet de son envoyé ; fournisseur_ms : tout le temps passé chez le fournisseur.
    assert number(f["premier_mot_ms"]) <= number(f["total_ms"])
    assert number(f["fournisseur_ms"]) <= number(f["total_ms"])


def test_tts_line_cut_mid_stream_is_an_error(monkeypatch, lines):
    response = h.post_tts("Bonjour", late_error="coupure", monkeypatch=monkeypatch)
    response.close()
    f = one(lines)
    assert f["statut"] == "erreur" and f["premier_mot_ms"] != "-"


def test_tts_failure_and_empty_text(monkeypatch, lines):
    h.post_tts("Bonjour", error="tts en panne", monkeypatch=monkeypatch).close()
    h.post_tts("   ", monkeypatch=monkeypatch).close()
    failed_call, empty = (h.fields(line) for line in lines)
    assert failed_call["statut"] == "erreur" and failed_call["fournisseur_ms"] != "-"
    assert empty["statut"] == "invalide" and empty["fournisseur_ms"] == "-"


# --- Requêtes refusées avant ou dans la route -------------------------------------------------------------


def test_chat_refused_by_the_csrf_check_leaves_no_line_but_stt_leaves_an_invalide_one(lines):
    client = h.app_module.app.test_client()
    refused = client.post("/chat", json={"message": "Bonjour"}, headers={"Origin": h.B}, base_url=h.B)
    assert refused.status_code == 403
    refused.close()
    assert lines == []  # le contrôle CSRF de /chat répond avant la route, donc avant la mesure
    refused = client.post(
        "/stt", data={}, content_type="multipart/form-data", headers={"Origin": h.app_module.SITE_URL},
        environ_base={"REMOTE_ADDR": h.next_ip()},
    )
    assert refused.status_code == 403
    refused.close()
    f = one(lines)
    assert f["route"] == "stt" and f["statut"] == "invalide" and f["fournisseur_ms"] == "-"


# --- Demande de photos seule (flux) : relecture automatique de la PR #435 -----------------------------------


PHOTO_QUESTION = "Montre-moi des photos de la Pointe des Almadies"


def test_a_photo_only_stream_that_reaches_its_end_is_ok_and_has_a_first_word(monkeypatch, lines):
    monkeypatch.setattr(h.app_module, "_fetch_topic_images", lambda *args, **kwargs: [])
    finish(post_chat(PHOTO_QUESTION))
    f = one(lines)
    assert f["route"] == "chat" and f["mode"] == "flux"
    assert f["statut"] == "ok", "un flux de photos mené à son terme était compté comme « abandon »"
    assert number(f["premier_mot_ms"]) <= number(f["total_ms"])


def test_a_photo_only_stream_that_fails_is_an_error(monkeypatch, lines):
    def boom(*args, **kwargs):
        raise RuntimeError("images en panne")

    monkeypatch.setattr(h.app_module, "_fetch_topic_images", boom)
    finish(post_chat(PHOTO_QUESTION))
    assert one(lines)["statut"] == "erreur"
