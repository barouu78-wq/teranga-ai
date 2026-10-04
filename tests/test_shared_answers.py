"""Partage des réponses : lien signé, falsification refusée, page sûre."""

import json
import os
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.shared_answers import open_token, sign_answer  # noqa: E402

SECRET = "s" * 64


def test_round_trip_keeps_question_answer_and_safe_sources():
    token = sign_answer(SECRET, "Que voir à Gorée ?", "La Maison des Esclaves.\n\nLe fort d'Estrées.", [
        {"title": "Unesco", "url": "https://whc.unesco.org/fr/list/26/"},
        {"title": "piège", "url": "javascript:alert(1)"},
    ], "fr")
    shared = open_token(SECRET, token)
    assert shared["question"] == "Que voir à Gorée ?"
    assert shared["answer"].startswith("La Maison des Esclaves.")
    assert shared["sources"] == [{"title": "Unesco", "url": "https://whc.unesco.org/fr/list/26/"}]
    assert shared["language"] == "fr"


def test_tampered_or_foreign_tokens_are_refused():
    token = sign_answer(SECRET, "q", "Réponse authentique", None, "en")
    data, mac = token.split(".")
    forged = sign_answer("autre-secret" * 4, "q", "Réponse inventée", None, "en")
    assert open_token(SECRET, forged) is None
    assert open_token(SECRET, forged.split(".")[0] + "." + mac) is None
    assert open_token(SECRET, data + "." + mac[:-2] + "AA") is None
    assert open_token(SECRET, "") is None
    assert open_token(SECRET, "x" * 20000) is None
    assert sign_answer(SECRET, "q", "   ") == ""


def _client():
    import app as app_module

    client = app_module.app.test_client()
    return app_module, client


def test_share_page_is_noindex_and_uses_a_nonce():
    _, client = _client()
    response = client.get("/partage", base_url="https://teranga-ai.fr")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'content="noindex,follow"' in html
    assert "textContent" in html and "innerHTML" not in html
    nonce = html.split('<script nonce="', 1)[1].split('"', 1)[0]
    assert f"'nonce-{nonce}'" in response.headers["Content-Security-Policy"]


def test_open_api_returns_the_signed_answer_only():
    app_module, client = _client()
    token = sign_answer(app_module.app.config["SECRET_KEY"], "Météo Dakar", "Ensoleillé.", None, "fr")
    ok = client.post("/api/share/open", json={"token": token}, base_url="https://teranga-ai.fr")
    assert ok.status_code == 200 and ok.get_json()["answer"] == "Ensoleillé."
    bad = client.post("/api/share/open", json={"token": token[:-3] + "abc"}, base_url="https://teranga-ai.fr")
    assert bad.status_code == 400


def test_chat_stream_ends_with_a_share_token(monkeypatch):
    app_module, client = _client()

    def fake_stream(payload, stream=True):
        yield SimpleNamespace(type="response.output_text.delta", delta="Bonjour ")
        yield SimpleNamespace(type="response.output_text.delta", delta="de Dakar.")

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_stream)
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat",
        json={"message": "Dis bonjour", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
        base_url="https://teranga-ai.fr",
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
    share = next(event["share"] for event in events if "share" in event)
    shared = open_token(app_module.app.config["SECRET_KEY"], share)
    assert shared["question"] == "Dis bonjour"
    assert shared["answer"] == "Bonjour de Dakar."
