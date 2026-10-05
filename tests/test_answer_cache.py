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


def test_second_identical_question_is_served_from_cache(monkeypatch):
    import app as app_module

    calls = []

    def fake_stream(payload, stream=True):
        calls.append(payload["message"])
        yield SimpleNamespace(type="response.output_text.delta", delta=REPLY)

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
