"""Réponse coupée par la limite de longueur : le chat le dit, et « continue » reprend où elle s'est arrêtée.

Avant, une réponse arrêtée par `max_output_tokens` (800 jetons, raisonnement compris) s'affichait en flux sans le
dire : elle finissait au milieu d'une phrase. Le client (static/home.js) n'affiche que le texte des événements `d` ;
la mention est donc ajoutée au texte lui-même. Le faux fournisseur remplace `client.responses.create` : tout le
reste (construction de la requête, `complete_reply`, route) est le code réel. Aucun appel réseau.
"""

import json
import os
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest

import app as app_module
import routes.chat as chat_routes
from services import backup_ai
from services.backup_ai import backup_complete, claude_events
from services.truncation import (
    CUT_NOTICES,
    cut_notice,
    ends_with_cut_notice,
    is_cut_by_length,
    mark_incomplete,
    prepare_cut_history,
    strip_cut_notice,
    with_cut_notice,
)

B = "https://teranga-ai.fr"
FR = CUT_NOTICES["fr"]
EN = CUT_NOTICES["en"]
CUT_TEXT = "Pour aller de Dakar à Saint-Louis, le plus simple est de prendre un car depuis la gare routière de Pompiers puis, à l'arrivée, un"
LAST_IP = [0]


def ip():
    LAST_IP[0] += 1
    return f"198.51.100.{100 + LAST_IP[0]}"


def delta(text):
    return SimpleNamespace(type="response.output_text.delta", delta=text)


def incomplete_event(text, reason="max_output_tokens"):
    details = SimpleNamespace(reason=reason) if reason is not None else None
    return SimpleNamespace(type="response.incomplete", response=SimpleNamespace(status="incomplete", incomplete_details=details, output_text=text))


def completed_event(text):
    return SimpleNamespace(type="response.completed", response=SimpleNamespace(status="completed", incomplete_details=None, output_text=text))


def response(text, status="completed", reason=None):
    details = SimpleNamespace(reason=reason) if reason else None
    return SimpleNamespace(output_text=text, status=status, incomplete_details=details, output=[])


class Provider:
    """Remplace client.responses.create : un flux (stream=True) ou une réponse complète (stream=False)."""

    def __init__(self, stream_events, full=None):
        self.stream_events = stream_events
        self.full = full
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(bool(kwargs.get("stream")))
        if kwargs.get("stream"):
            return iter(self.stream_events)
        return self.full if self.full is not None else response("")


@pytest.fixture
def provider(monkeypatch):
    def install(stream_events, full=None):
        fake = Provider(stream_events, full)
        monkeypatch.setattr(app_module.client.responses, "create", fake)
        return fake

    return install


def post(message, *, history=(), json_mode=False, language="fr", remote=None):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    headers = {"X-CSRF-Token": token, "Origin": B}
    if json_mode:
        headers["X-Teranga-Mode"] = "json"
    body = {"message": message, "history": [*history, {"role": "user", "content": message}], "language": language, "audience": "tourist"}
    return client.post("/chat", json=body, headers=headers, base_url=B, environ_base={"REMOTE_ADDR": remote or ip()})


def events_of(result):
    return [json.loads(line) for line in result.get_data(as_text=True).splitlines() if line.strip()]


def text_of(events):
    return "".join(e.get("d", "") for e in events)


QUESTION = "Comment aller de Dakar à Saint-Louis en transport ?"


# --- Flux ----------------------------------------------------------------------------------------------------


def test_a_stream_cut_by_the_length_limit_says_so(provider):
    provider([delta(CUT_TEXT), incomplete_event(CUT_TEXT)])
    events = events_of(post(QUESTION))
    text = text_of(events)
    assert text == CUT_TEXT + "\n\n" + FR
    # Le client n'affiche que les événements `d` : la mention en est un, et elle précède les événements de fin.
    texts = [i for i, e in enumerate(events) if "d" in e]
    assert events[texts[-1]]["d"] == "\n\n" + FR and texts[-1] < next(i for i, e in enumerate(events) if e.get("done"))
    assert events[-1] == {"done": True}


def test_the_notice_is_in_english_for_english_users(provider):
    provider([delta("The simplest way is to take a coach from the Pompiers station, then"), incomplete_event("x")])
    assert text_of(events_of(post("How do I get from Dakar to Saint-Louis?", language="en"))).endswith("\n\n" + EN)


def test_wolof_and_fulani_users_get_the_french_notice(provider):
    provider([delta(CUT_TEXT), incomplete_event(CUT_TEXT)])
    assert text_of(events_of(post(QUESTION, language="wo"))).endswith(FR)


def test_a_complete_answer_gets_no_notice(provider):
    full = "Le car part de la gare routière de Pompiers, compter environ quatre heures de route."
    provider([delta(full), completed_event(full)])
    text = text_of(events_of(post(QUESTION)))
    assert text == full and "Réponse coupée" not in text


def test_an_answer_stopped_by_the_content_filter_gets_no_length_notice(provider):
    """« continue » n'y changerait rien : pas de mention."""
    provider([delta(CUT_TEXT), incomplete_event(CUT_TEXT, reason="content_filter")])
    assert text_of(events_of(post(QUESTION))) == CUT_TEXT


def test_an_incomplete_event_without_reason_counts_as_a_length_stop(provider):
    """Claude (via backup_ai) ne donne pas de raison."""
    provider([delta(CUT_TEXT), incomplete_event(CUT_TEXT, reason=None)])
    assert text_of(events_of(post(QUESTION))).endswith(FR)


def test_a_cut_stream_is_never_cached(provider):
    fake = provider([delta(CUT_TEXT * 2), incomplete_event(CUT_TEXT * 2)])
    message = "Question coupée à ne pas mettre en cache 1"
    events_of(post(message))
    events_of(post(message))
    assert fake.calls.count(True) == 2, "la seconde demande doit rappeler le fournisseur"


def test_a_complete_answer_is_still_cached(provider):
    full = "Le car part de la gare routière de Pompiers, compter environ quatre heures de route et prévoir la monnaie."
    fake = provider([delta(full), completed_event(full)])
    message = "Question complète à mettre en cache 2"
    first = text_of(events_of(post(message)))
    second = text_of(events_of(post(message)))
    assert first == second == full and fake.calls.count(True) == 1


def test_a_cut_stream_with_no_visible_text_retries_and_says_so(provider):
    """Le raisonnement a mangé toute la limite : flux vide, puis appel complet qui revient coupé."""
    fake = provider([incomplete_event("")], full=response(CUT_TEXT, status="incomplete", reason="max_output_tokens"))
    text = text_of(events_of(post("Question dont le raisonnement mange tout 3")))
    assert text == CUT_TEXT + "\n\n" + FR and fake.calls == [True, False]


def test_a_cut_stream_with_no_visible_text_whose_retry_completes_has_no_notice(provider):
    full = "Le car part de la gare routière de Pompiers, compter environ quatre heures de route."
    provider([incomplete_event("")], full=response(full))
    assert text_of(events_of(post("Question dont le raisonnement mange tout 4"))) == full


def test_a_total_failure_after_a_cut_shows_a_message_but_never_the_cut_notice(provider):
    """Rien de visible et l'appel complet est vide aussi : le message de secours n'est pas une réponse coupée."""
    provider([incomplete_event("")], full=response("", status="incomplete", reason="max_output_tokens"))
    text = text_of(events_of(post("Question sans aucune réponse visible 5")))
    assert text.strip() and "Réponse coupée" not in text


# --- Mode JSON ----------------------------------------------------------------------------------------------


def test_json_mode_says_so_and_does_not_cache(provider):
    fake = provider([], full=response(CUT_TEXT, status="incomplete", reason="max_output_tokens"))
    message = "Question JSON coupée 6"
    for _ in range(2):
        data = post(message, json_mode=True).get_json()
        assert data["reply"] == CUT_TEXT + "\n\n" + FR
    assert fake.calls == [False, False]


def test_json_mode_in_english(provider):
    provider([], full=response(CUT_TEXT, status="incomplete", reason="max_output_tokens"))
    assert post("Cut question in English 7", json_mode=True, language="en").get_json()["reply"].endswith(EN)


def test_json_mode_complete_answer_is_untouched(provider):
    full = "Le car part de la gare routière de Pompiers, compter environ quatre heures de route."
    provider([], full=response(full))
    assert post("Question JSON complète 8", json_mode=True).get_json()["reply"] == full


# --- Claude : IA principale et IA de secours -----------------------------------------------------------------


class FakeStream:
    def __init__(self, texts, stop_reason="end_turn"):
        self.text_stream = iter(texts)
        block = SimpleNamespace(type="text", text="".join(texts), citations=[])
        self.message = SimpleNamespace(stop_reason=stop_reason, content=[block])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClaude:
    def __init__(self, stream):
        self.stream = stream
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=lambda **params: stream))


def test_claude_as_primary_says_so_when_it_hits_max_tokens(monkeypatch):
    """Les événements viennent du vrai `claude_events` (stop_reason max_tokens), la route est la vraie."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    claude = FakeClaude(FakeStream([CUT_TEXT], stop_reason="max_tokens"))
    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", lambda payload, stream=False: claude_events("Q", client=claude))
    assert text_of(events_of(post("Question pour Claude principal coupée 9"))) == CUT_TEXT + "\n\n" + FR
    claude = FakeClaude(FakeStream([CUT_TEXT], stop_reason="end_turn"))
    assert text_of(events_of(post("Question pour Claude principal complète 10"))) == CUT_TEXT


def test_claude_as_backup_says_so_in_the_users_language(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("AI_PRINCIPALE", raising=False)
    monkeypatch.setattr(app_module.client.responses, "create", lambda **kw: (_ for _ in ()).throw(RuntimeError("503 upstream unavailable")))
    claude = FakeClaude(FakeStream([CUT_TEXT], stop_reason="max_tokens"))
    monkeypatch.setattr(backup_ai, "_client", lambda: claude)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", lambda payload: (_ for _ in ()).throw(RuntimeError("503")))
    assert post("Question secours Claude coupée 11", json_mode=True).get_json()["reply"] == CUT_TEXT + "\n\n" + FR
    claude.stream = FakeStream([CUT_TEXT], stop_reason="max_tokens")
    claude.beta = SimpleNamespace(messages=SimpleNamespace(stream=lambda **params: claude.stream))
    assert post("Backup answer cut in English 12", json_mode=True, language="en").get_json()["reply"].endswith(EN)


def test_backup_complete_only_adds_the_notice_when_asked():
    """Le planificateur appelle backup_complete sans `language` : son texte (du JSON) reste tel quel."""
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    try:
        cut = FakeClaude(FakeStream(["{\"days\": [1, 2"], stop_reason="max_tokens"))
        assert backup_complete("Plan", client=cut) == "{\"days\": [1, 2"
        cut = FakeClaude(FakeStream(["Début"], stop_reason="max_tokens"))
        assert backup_complete("Q", client=cut, language="fr") == "Début\n\n" + FR
        ok = FakeClaude(FakeStream(["Complet."], stop_reason="end_turn"))
        assert backup_complete("Q", client=ok, language="fr") == "Complet."
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)


# --- Brique de base --------------------------------------------------------------------------------------------


def test_notice_helpers():
    assert cut_notice("fr") == FR and cut_notice("en") == EN and cut_notice("wo") == FR and cut_notice("") == FR
    assert with_cut_notice("Début", "fr") == "Début\n\n" + FR
    assert with_cut_notice("Début  \n", "en") == "Début\n\n" + EN
    assert with_cut_notice("", "fr") == "" and with_cut_notice("   ", "fr") == "   " and with_cut_notice(None) == ""
    once = with_cut_notice("Début", "fr")
    assert with_cut_notice(once, "fr") == once and with_cut_notice(once, "en") == once  # jamais deux fois
    assert ends_with_cut_notice(once) and ends_with_cut_notice(once + "  \n") and not ends_with_cut_notice("Début")
    assert strip_cut_notice(once) == "Début" and strip_cut_notice("Début") == "Début" and strip_cut_notice(None) == ""


def test_the_notice_asks_for_a_word_the_site_understands_as_a_follow_up():
    from services.intelligence import _BACK_REFERENCES

    assert "continue" in _BACK_REFERENCES and "« continue »" in FR and "“continue”" in EN


@pytest.mark.parametrize("response_obj,expected", [
    (SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="max_output_tokens")), True),
    (SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="max_tokens")), True),
    (SimpleNamespace(status="incomplete", incomplete_details=None), True),
    (SimpleNamespace(status="incomplete"), True),
    ({"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}, True),
    ({"status": "incomplete", "incomplete_details": {"reason": "content_filter"}}, False),
    (SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="content_filter")), False),
    (SimpleNamespace(status="completed"), False),
    (SimpleNamespace(output_text="x"), False),
    (None, False),
])
def test_is_cut_by_length(response_obj, expected):
    assert is_cut_by_length(response_obj) is expected


def test_mark_incomplete_flags_the_payload():
    payload = {}
    assert mark_incomplete(payload, SimpleNamespace(status="incomplete")) is True
    assert payload == {"reply_incomplete": True, "reply_cut": True}
    payload = {}
    assert mark_incomplete(payload, SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="content_filter"))) is False
    assert payload == {"reply_incomplete": True}
    payload = {}
    assert mark_incomplete(payload, SimpleNamespace(status="completed")) is False and payload == {}


# --- « continue » : le modèle voit la fin de sa réponse coupée -------------------------------------------------


LONG_ANSWER = " ".join(f"Étape {n} : prendre le car numéro {n} jusqu'à l'arrêt suivant." for n in range(1, 60))


def test_prepare_cut_history_keeps_the_end_of_a_long_cut_answer():
    history = [
        {"role": "user", "content": "Comment aller à Saint-Louis ?"},
        {"role": "assistant", "content": with_cut_notice(LONG_ANSWER, "fr")},
        {"role": "user", "content": "continue"},
    ]
    assert len(LONG_ANSWER) > 2500
    prepared, cut = prepare_cut_history(history, 1400)
    assert cut is True
    answer = prepared[1]["content"]
    assert len(answer) <= 1400 and "[…]" in answer and not ends_with_cut_notice(answer)
    assert answer.startswith("Étape 1 :") and answer.endswith(LONG_ANSWER[-120:])
    assert prepared[0] == history[0] and prepared[2] == history[2]
    assert history[1]["content"].endswith(FR), "l'historique reçu n'est pas modifié"


def test_prepare_cut_history_short_cut_answer_loses_only_the_notice():
    history = [{"role": "assistant", "content": with_cut_notice("Début de réponse", "en")}, {"role": "user", "content": "continue"}]
    assert prepare_cut_history(history, 1400) == ([{"role": "assistant", "content": "Début de réponse"}, history[1]], True)


@pytest.mark.parametrize("history", [
    [{"role": "assistant", "content": "Réponse complète."}, {"role": "user", "content": "Merci"}],
    [{"role": "user", "content": "Bonjour"}],
    [],
])
def test_prepare_cut_history_without_a_cut_answer(history):
    prepared, cut = prepare_cut_history(history, 1400)
    assert prepared == history and cut is False


def test_prepare_cut_history_only_the_last_assistant_turn_counts():
    old_cut = {"role": "assistant", "content": with_cut_notice("Vieille réponse coupée", "fr")}
    history = [old_cut, {"role": "user", "content": "Autre question"}, {"role": "assistant", "content": "Réponse complète."}, {"role": "user", "content": "Merci"}]
    prepared, cut = prepare_cut_history(history, 1400)
    assert cut is False and prepared[0]["content"] == "Vieille réponse coupée"  # la mention n'est jamais recopiée au modèle


def test_prepare_cut_history_ignores_malformed_history():
    assert prepare_cut_history("pas une liste", 1400) == ("pas une liste", False)
    mixed = ["texte", {"role": "assistant"}, {"role": "assistant", "content": with_cut_notice("Fin", "fr")}, 3]
    prepared, cut = prepare_cut_history(mixed, 1400)
    assert cut is True and prepared[:2] == mixed[:2] and prepared[2]["content"] == "Fin" and prepared[3] == 3


def parse(message, history):
    body = {"message": message, "history": [*history, {"role": "user", "content": message}], "language": "fr", "audience": "tourist"}
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def test_continue_after_a_cut_answer_gives_the_model_the_end_of_it():
    history = [
        {"role": "user", "content": "Comment aller de Dakar à Saint-Louis ?"},
        {"role": "assistant", "content": with_cut_notice(LONG_ANSWER, "fr")},
    ]
    payload = parse("continue", history)
    assert LONG_ANSWER[-100:] in payload["input_text"], "le modèle doit voir où la réponse s'est arrêtée"
    assert "Réponse coupée" not in payload["input_text"] and "Réponse coupée" not in payload["instructions"]
    assert "SUITE D'UNE RÉPONSE COUPÉE" in payload["instructions"]
    assert "<demande_utilisateur>\ncontinue\n</demande_utilisateur>" in payload["input_text"]


def test_the_model_only_saw_the_beginning_of_a_long_answer_without_the_preparation():
    """Ce que faisait le chat : l'historique est limité aux 1400 premiers caractères de chaque tour."""
    history = [
        {"role": "user", "content": "Comment aller de Dakar à Saint-Louis ?"},
        {"role": "assistant", "content": LONG_ANSWER},  # sans mention : aucun traitement
    ]
    payload = parse("continue", history)
    assert LONG_ANSWER[-100:] not in payload["input_text"] and "SUITE D'UNE RÉPONSE COUPÉE" not in payload["instructions"]


def test_a_normal_conversation_gets_no_cut_instruction():
    history = [{"role": "user", "content": "Quelle langue parle-t-on ?"}, {"role": "assistant", "content": "Le wolof, le français et le pulaar."}]
    assert "SUITE D'UNE RÉPONSE COUPÉE" not in parse("Merci", history)["instructions"]


def test_the_continue_request_reaches_the_provider_with_the_end_of_the_answer(provider, monkeypatch):
    fake_events = [delta("Étape 60 : arrivée à Saint-Louis."), completed_event("Étape 60 : arrivée à Saint-Louis.")]
    seen = {}
    fake = provider(fake_events)
    original = fake.__call__

    def spy(**kwargs):
        seen["input"] = kwargs["input"]
        seen["instructions"] = kwargs["instructions"]
        return original(**kwargs)

    monkeypatch.setattr(app_module.client.responses, "create", spy)
    history = [{"role": "user", "content": "Comment aller de Dakar à Saint-Louis ?"}, {"role": "assistant", "content": with_cut_notice(LONG_ANSWER, "fr")}]
    text = text_of(events_of(post("continue", history=history)))
    assert text == "Étape 60 : arrivée à Saint-Louis."
    assert LONG_ANSWER[-100:] in seen["input"] and "SUITE D'UNE RÉPONSE COUPÉE" in seen["instructions"]
