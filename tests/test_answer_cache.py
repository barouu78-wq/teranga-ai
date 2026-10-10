import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import json
from types import SimpleNamespace

from services.answer_cache import AnswerCache, cache_key, replay_chunks

BASE = {"message": "Que visiter à Dakar ?", "language": "fr", "audience": "tourist", "use_web": False}
REPLY = "À Dakar, commence par l'île de Gorée, puis le monument de la Renaissance et le marché Kermel."


def test_cache_key_ignores_case_spaces_and_final_punctuation():
    a = cache_key(BASE, {}, model="m")
    b = cache_key({**BASE, "message": "  que visiter à   DAKAR"}, {}, model="m")
    assert a and a == b
    assert cache_key({**BASE, "language": "en"}, {}, model="m") != a
    assert cache_key(BASE, {}, model="autre-modele") != a


def test_personal_or_changing_requests_are_never_cached():
    assert cache_key(BASE, {"history": [{"role": "user", "content": "x"}]}, model="m") is None
    assert cache_key(BASE, {"trip_context": "Dakar 3 jours"}, model="m") is None
    assert cache_key(BASE, {"context_place": "Gorée"}, model="m") is None
    for flag in ("use_web", "planner", "deep_reasoning", "live_weather", "photo_only"):
        assert cache_key({**BASE, flag: True}, {}, model="m") is None
    assert cache_key({**BASE, "action_request": {"enabled": True}}, {}, model="m") is None
    assert cache_key({**BASE, "message": "x" * 300}, {}, model="m") is None


def test_memory_cache_roundtrip_expiry_and_short_replies():
    cache = AnswerCache(ttl=60)
    key = cache_key(BASE, {}, model="m")
    assert cache.set(key, reply="Oui.") is False  # trop court pour être utile
    assert cache.set(key, reply=REPLY, sources=[{"url": "https://x"}])
    assert cache.get(key)["reply"] == REPLY
    cache._memory[key] = (0, cache._memory[key][1])
    assert cache.get(key) is None
    assert AnswerCache(enabled=False).set(key, reply=REPLY) is False


class _BrokenRedis:
    def get(self, key):
        raise ConnectionError("down")

    def setex(self, *args):
        raise ConnectionError("down")


def test_redis_failure_falls_back_to_memory():
    cache = AnswerCache(_BrokenRedis(), ttl=60)
    key = cache_key(BASE, {}, model="m")
    assert cache.set(key, reply=REPLY)
    assert cache.get(key)["reply"] == REPLY


def test_replay_chunks_rebuild_the_exact_text():
    chunks = list(replay_chunks(REPLY, size=20))
    assert "".join(chunks) == REPLY and len(chunks) > 2


def _ask_factory(app_module, ip="203.0.113.150"):
    client = app_module.app.test_client()

    def ask(message):
        token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
        client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
        response = client.post(
            "/chat",
            json={"message": message, "language": "fr"},
            headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
            base_url="https://teranga-ai.fr",
            environ_base={"REMOTE_ADDR": ip},
        )
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        return "".join(e.get("d", "") for e in events), events

    return ask


def test_truncated_or_fallback_answers_are_not_cached(monkeypatch):
    """Une réponse coupée (response.incomplete) ou de secours ne doit pas être resservie à tout le monde."""
    import app as app_module

    calls = []

    def cut_stream(payload, stream=True):
        calls.append(payload["message"])
        yield SimpleNamespace(type="response.output_text.delta", delta=REPLY[:75])
        yield SimpleNamespace(type="response.incomplete", response=SimpleNamespace(output_text=REPLY[:75]))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", cut_stream)
    ask = _ask_factory(app_module)
    ask("Que visiter à Dakar ?")
    ask("que visiter à dakar")
    assert len(calls) == 2  # rien n'a été mis en cache : le modèle est rappelé


def test_second_identical_question_is_served_from_cache(monkeypatch):
    import app as app_module

    calls = []

    def fake_stream(payload, stream=True):
        calls.append(payload["message"])
        yield SimpleNamespace(type="response.output_text.delta", delta=REPLY)
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text=REPLY))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_stream)
    client = app_module.app.test_client()

    def ask(message):
        token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
        client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
        response = client.post(
            "/chat",
            json={"message": message, "language": "fr"},
            headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
            base_url="https://teranga-ai.fr",
        )
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        return "".join(e.get("d", "") for e in events), events

    first, _ = ask("Que visiter à Dakar ?")
    second, events = ask("que visiter à dakar")
    assert first == second == REPLY
    assert len(calls) == 1
    assert events[-1] == {"done": True} and any("share" in e for e in events)


# --- Forme réelle du client : static/home.js ajoute la question à l'historique AVANT l'envoi ---------------------


def _site_turn(role, content):
    return {"role": role, "content": content}


def test_first_question_sent_like_the_site_is_cacheable():
    """Le site envoie history=[la question courante] : c'est une première question, pas un suivi."""
    site_body = {"history": [_site_turn("user", "Que visiter à Dakar ?")]}
    assert cache_key(BASE, site_body, model="m") == cache_key(BASE, {}, model="m")
    # Casse, espaces et ponctuation finale ne comptent pas, comme pour le message lui-même.
    retyped = {"history": [_site_turn("user", "  que visiter à   DAKAR ")]}
    assert cache_key(BASE, retyped, model="m") == cache_key(BASE, {}, model="m")


def test_any_earlier_turn_still_disables_the_cache():
    here = _site_turn("user", "Que visiter à Dakar ?")
    for history in (
        [_site_turn("user", "Bonjour"), here],  # message précédent
        [_site_turn("user", "Parle-moi de Gorée"), _site_turn("assistant", "Gorée est une île."), here],
        [_site_turn("assistant", "Bienvenue !"), here],  # même sans question avant
        [here, _site_turn("assistant", "Gorée, Lac Rose…"), here],  # la même question posée deux fois
        [here, _site_turn("assistant", "Gorée, Lac Rose…")],  # la question n'est pas le dernier tour
        [_site_turn("user", "Autre question")],  # le dernier tour n'est pas la question courante
        [here, "texte inattendu"],  # historique mal formé : jamais de cache
        "pas une liste",
    ):
        assert cache_key(BASE, {"history": history}, model="m") is None, history


def test_empty_history_items_do_not_count_as_a_previous_turn():
    body = {"history": [_site_turn("user", "   "), _site_turn("user", "Que visiter à Dakar ?")]}
    assert cache_key(BASE, body, model="m") == cache_key(BASE, {}, model="m")


def _site_client(app_module, ip):
    """Même corps que static/home.js : la question est déjà le dernier élément de history."""
    client = app_module.app.test_client()

    def ask(message, history=(), json_mode=False):
        token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
        client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
        headers = {"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"}
        if json_mode:
            headers["X-Teranga-Mode"] = "json"
        response = client.post(
            "/chat",
            json={"message": message, "history": [*history, _site_turn("user", message)], "language": "fr", "audience": "tourist"},
            headers=headers,
            base_url="https://teranga-ai.fr",
            environ_base={"REMOTE_ADDR": ip},
        )
        if json_mode:
            return response.get_json()
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        return "".join(e.get("d", "") for e in events), events

    return ask


def test_first_question_from_the_site_is_served_from_cache(monkeypatch):
    import app as app_module

    calls = []

    def fake_stream(payload, stream=True):
        calls.append(payload["message"])
        yield SimpleNamespace(type="response.output_text.delta", delta=REPLY)
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text=REPLY))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_stream)
    ask = _site_client(app_module, "203.0.113.151")
    first, _ = ask("Que visiter à Dakar ?")
    second, events = ask("que visiter à dakar")
    assert first == second == REPLY
    assert len(calls) == 1  # le second visiteur n'a coûté aucun appel au modèle
    assert events[-1] == {"done": True}


def test_follow_up_from_the_site_is_never_served_from_cache(monkeypatch):
    import app as app_module

    calls = []

    def fake_stream(payload, stream=True):
        calls.append(payload["input_text"])
        yield SimpleNamespace(type="response.output_text.delta", delta=REPLY)
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text=REPLY))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_stream)
    ask = _site_client(app_module, "203.0.113.152")
    ask("Combien coûte un taxi de l'AIBD à Dakar ?")
    # « merci » ne doit pas recevoir la réponse mise en cache d'une autre conversation.
    earlier = [_site_turn("user", "Parle-moi de Gorée"), _site_turn("assistant", "Gorée est une île au large de Dakar.")]
    ask("merci", earlier)
    ask("merci", earlier)
    assert len(calls) == 3


def test_truncated_json_answer_is_not_cached(monkeypatch):
    """Mode JSON : une réponse coupée (limite de longueur) ne doit pas être resservie à tout le monde."""
    import app as app_module

    calls = []

    def cut_reply(payload):
        calls.append(payload["message"])
        payload["reply_incomplete"] = True
        return REPLY[:75] + " et le", [], None, None

    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", cut_reply)
    ask = _site_client(app_module, "203.0.113.153")
    assert ask("Que visiter à Dakar ?", json_mode=True)["reply"].endswith("et le")
    ask("que visiter à dakar", json_mode=True)
    assert len(calls) == 2


def test_complete_json_answer_is_cached(monkeypatch):
    import app as app_module

    calls = []

    def full_reply(payload):
        calls.append(payload["message"])
        return REPLY, [], None, None

    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", full_reply)
    ask = _site_client(app_module, "203.0.113.154")
    first = ask("Que visiter à Dakar ?", json_mode=True)
    second = ask("que visiter à dakar", json_mode=True)
    assert first["reply"] == second["reply"] == REPLY
    assert len(calls) == 1


def test_service_flags_an_incomplete_provider_response():
    from services.chat_service import build_chat_service

    class Logger:
        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

    def make(status):
        def fake_create(client, payload, **kwargs):
            return SimpleNamespace(output_text=REPLY[:50], status=status)

        return build_chat_service(
            client=object(), model="gpt-5.6-luna", complex_model="gpt-5.6-sol", logger=Logger(),
            build_model_kwargs=lambda payload, **kw: {"model": kw["model"]},
            reasoning_effort=lambda web, planner: "low", search_context_size=lambda d, p: "low",
            preferred_domains=lambda d: (), create_openai_response=fake_create, clean_answer=lambda t: t,
            extract_sources=lambda r: [], fetch_topic_images=lambda m: None, lookup_map=lambda q, e: None,
            should_fetch_map=lambda q: False,
        )

    cut, whole = {"message": "x"}, {"message": "x"}
    make("incomplete")["complete_reply"](cut)
    make("completed")["complete_reply"](whole)
    assert cut.get("reply_incomplete") is True
    assert not whole.get("reply_incomplete")
