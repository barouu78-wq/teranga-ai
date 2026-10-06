"""IA de secours (Claude) : prend le relais quand OpenAI échoue, seulement si elle est configurée."""

import json
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
import routes.chat as chat_routes  # noqa: E402
import services.trip_planner as tp  # noqa: E402
from services.backup_ai import backup_complete, backup_enabled  # noqa: E402

B = "https://teranga-ai.fr"


def _broken(*_args, **_kwargs):
    raise RuntimeError("Error code: 503 - upstream unavailable")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_backup_is_off_without_key_and_parses_text(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not backup_enabled() and backup_complete("Bonjour") == ""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    sent = {}

    def post(url, json, headers, timeout):
        sent.update(url=url, body=json, headers=headers)
        return FakeResponse({"content": [{"type": "text", "text": "Salam "}, {"type": "text", "text": "!"}]})

    assert backup_complete("Bonjour", system="Sois bref", http_post=post) == "Salam !"
    assert sent["url"].startswith("https://api.anthropic.com/") and sent["headers"]["x-api-key"] == "sk-test"
    assert sent["body"]["system"] == "Sois bref" and sent["body"]["messages"][0]["content"] == "Bonjour"


def test_chat_uses_backup_when_openai_is_down(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(chat_routes, "backup_complete", lambda prompt, **kw: "Réponse de secours sur le Sénégal.")
    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", _broken)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", _broken)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post("/chat", json={"message": "Question secours 7", "language": "fr"},
                           headers={"X-CSRF-Token": token, "Origin": B}, base_url=B)
    text = "".join(json.loads(line).get("d", "") for line in response.get_data(as_text=True).splitlines() if line.strip())
    assert "Réponse de secours" in text


def test_planner_uses_backup_when_openai_is_down(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    plan = json.dumps({"summary": "Secours", "days": [{"day": 1, "title": "J", "region": "Dakar"}, {"day": 2, "title": "K", "region": "Dakar"}]})
    monkeypatch.setattr(tp, "backup_complete", lambda prompt, **kw: plan)
    monkeypatch.setattr(tp, "_create", _broken)
    client = app_module.app.test_client()
    body = {"lang": "fr", "arrival": "2026-11-10", "departure": "2026-11-12", "adults": 2, "children": 0,
            "interests": [], "budget": "Confort", "pace": "Équilibré", "regions": ["Dakar"]}
    for stream in ("1", ""):
        response = client.post("/api/trip-planner", json=body, headers={"Origin": B, "X-Teranga-Stream": stream}, base_url=B)
        raw = response.get_data(as_text=True)
        assert "Secours" in raw and '"error"' not in raw
