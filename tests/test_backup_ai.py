"""IA de secours (Claude) : prend le relais quand OpenAI échoue, seulement si elle est configurée."""

import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
import routes.chat as chat_routes  # noqa: E402
import services.chat_service as chat_service_module  # noqa: E402
import services.trip_planner as tp  # noqa: E402
from services.backup_ai import backup_complete, backup_enabled, claude_events, claude_is_primary  # noqa: E402

B = "https://teranga-ai.fr"


def _broken(*_args, **_kwargs):
    raise RuntimeError("Error code: 503 - upstream unavailable")


class FakeStream:
    def __init__(self, texts, stop_reason="end_turn", citations=()):
        self.text_stream = iter(texts)
        block = SimpleNamespace(type="text", text="".join(texts), citations=list(citations))
        self.message = SimpleNamespace(stop_reason=stop_reason, content=[block])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, *streams):
        self.streams = list(streams)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **params):
        self.calls.append(params)
        return self.streams.pop(0)


def test_backup_is_off_without_key_and_parses_text(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not backup_enabled() and backup_complete("Bonjour") == ""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fake = FakeClient(FakeStream(["Salam ", "!"]))
    assert backup_complete("Bonjour", system="Sois bref", client=fake) == "Salam !"
    params = fake.calls[0]
    assert params["system"] == "Sois bref" and params["messages"][0]["content"] == "Bonjour"
    assert params["fallbacks"] == "default" and params["betas"] == ["server-side-fallback-2026-07-01"]
    assert "tools" not in params


def test_claude_events_web_sources_pause_and_refusal(monkeypatch):
    cite = SimpleNamespace(url="https://www.au-senegal.com/x", title="Au Sénégal")
    fake = FakeClient(FakeStream(["Début "], stop_reason="pause_turn"), FakeStream(["fin."], citations=[cite]))
    events = list(claude_events("Météo Dakar", web=True, client=fake))
    assert [e.delta for e in events if e.type == "response.output_text.delta"] == ["Début ", "fin."]
    assert events[-1].type == "response.completed" and events[-1].response.output_text == "Début fin."
    assert events[-1].response.sources == [{"url": "https://www.au-senegal.com/x", "title": "Au Sénégal"}]
    assert fake.calls[0]["tools"][0]["type"] == "web_search_20260209"
    assert fake.calls[1]["messages"][-1]["role"] == "assistant"
    with pytest.raises(RuntimeError):
        list(claude_events("x", client=FakeClient(FakeStream([], stop_reason="refusal"))))
    truncated = list(claude_events("x", client=FakeClient(FakeStream(["a"], stop_reason="max_tokens"))))
    assert truncated[-1].type == "response.incomplete"
    # Même signal que l'API Responses d'OpenAI : la route ne met pas une réponse coupée en cache.
    assert truncated[-1].response.status == "incomplete"
    assert events[-1].response.status == "completed"


def test_primary_switch_needs_key_and_value(monkeypatch):
    monkeypatch.setenv("AI_PRINCIPALE", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not claude_is_primary()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert claude_is_primary()
    monkeypatch.setenv("AI_PRINCIPALE", "openai")
    assert not claude_is_primary()


def _chat(ip, message):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post("/chat", json={"message": message, "language": "fr"},
                           headers={"X-CSRF-Token": token, "Origin": B}, base_url=B,
                           environ_base={"REMOTE_ADDR": ip})
    return "".join(json.loads(line).get("d", "") for line in response.get_data(as_text=True).splitlines() if line.strip())


def test_chat_uses_claude_as_primary_then_openai_as_backup(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "claude")
    seen = {}

    def fake_events(prompt, **kw):
        seen.update(kw)
        yield SimpleNamespace(type="response.output_text.delta", delta="Bonjour de Claude.")
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text="Bonjour de Claude.", sources=[]))

    monkeypatch.setattr(chat_service_module, "claude_events", fake_events)
    assert "Bonjour de Claude" in _chat("203.0.113.73", "Question principale 1")
    assert "system" in seen

    def broken_events(prompt, **kw):
        raise RuntimeError("Claude overloaded")
        yield  # pragma: no cover

    class OpenAIEvent:
        type = "response.output_text.delta"
        delta = "Réponse OpenAI de relais."

    monkeypatch.setattr(chat_service_module, "claude_events", broken_events)
    calls = []

    def openai_stub(client, payload, **kw):
        calls.append(kw.get("stream"))
        return iter([OpenAIEvent()])

    service = chat_service_module.build_chat_service(
        client=None, model="m", logger=app_module.app.logger, build_model_kwargs=lambda *a, **k: {},
        reasoning_effort=None, search_context_size=None, preferred_domains=None,
        create_openai_response=openai_stub, clean_answer=lambda t: t, extract_sources=lambda *a: [],
        fetch_topic_images=None, lookup_map=None, should_fetch_map=None,
    )
    events = list(service["create_response"]({"message": "Q", "input_text": "Q"}, True))
    assert [e.delta for e in events] == ["Réponse OpenAI de relais."] and calls == [True]


def test_chat_uses_backup_when_openai_is_down(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("AI_PRINCIPALE", raising=False)
    monkeypatch.setattr(chat_routes, "backup_complete", lambda prompt, **kw: "Réponse de secours sur le Sénégal.")
    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", _broken)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", _broken)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post("/chat", json={"message": "Question secours 7", "language": "fr"},
                           headers={"X-CSRF-Token": token, "Origin": B}, base_url=B,
                           environ_base={"REMOTE_ADDR": "203.0.113.71"})
    text = "".join(json.loads(line).get("d", "") for line in response.get_data(as_text=True).splitlines() if line.strip())
    assert "Réponse de secours" in text


def test_planner_uses_backup_when_openai_is_down(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("AI_PRINCIPALE", raising=False)
    plan = json.dumps({"summary": "Secours", "days": [{"day": 1, "title": "J", "region": "Dakar"}, {"day": 2, "title": "K", "region": "Dakar"}]})
    monkeypatch.setattr(tp, "backup_complete", lambda prompt, **kw: plan)
    monkeypatch.setattr(tp, "_create", _broken)
    client = app_module.app.test_client()
    body = {"lang": "fr", "arrival": "2026-11-10", "departure": "2026-11-12", "adults": 2, "children": 0,
            "interests": [], "budget": "Confort", "pace": "Équilibré", "regions": ["Dakar"]}
    for stream in ("1", ""):
        response = client.post("/api/trip-planner", json=body, headers={"Origin": B, "X-Teranga-Stream": stream}, base_url=B,
                               environ_base={"REMOTE_ADDR": "203.0.113.72"})
        raw = response.get_data(as_text=True)
        assert "Secours" in raw and '"error"' not in raw


def test_planner_uses_claude_as_primary(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "claude")
    plan = json.dumps({"summary": "Plan Claude", "days": [{"day": 1, "title": "J", "region": "Dakar"}, {"day": 2, "title": "K", "region": "Dakar"}]})

    def fake_events(prompt, **kw):
        yield SimpleNamespace(type="response.output_text.delta", delta=plan)
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text=plan, sources=[]))

    monkeypatch.setattr(tp, "claude_events", fake_events)
    monkeypatch.setattr(tp, "claude_response", lambda prompt, **kw: SimpleNamespace(output_text=plan, sources=[]))
    monkeypatch.setattr(tp, "_create", _broken)
    client = app_module.app.test_client()
    body = {"lang": "fr", "arrival": "2026-11-10", "departure": "2026-11-12", "adults": 2, "children": 0,
            "interests": [], "budget": "Confort", "pace": "Équilibré", "regions": ["Dakar"]}
    for stream in ("1", ""):
        response = client.post("/api/trip-planner", json=body, headers={"Origin": B, "X-Teranga-Stream": stream}, base_url=B,
                               environ_base={"REMOTE_ADDR": "203.0.113.74"})
        raw = response.get_data(as_text=True)
        assert "Plan Claude" in raw and '"error"' not in raw
