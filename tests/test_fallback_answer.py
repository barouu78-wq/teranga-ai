"""IA en panne : Teranga répond quand même avec sa base pour un lieu ou un plat connu."""

import json
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.fallback_answer import knowledge_fallback  # noqa: E402

B = "https://teranga-ai.fr"


def _broken(*_args, **_kwargs):
    raise RuntimeError("Error code: 503 - upstream unavailable")


def _post(monkeypatch, message, json_mode=False):
    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", _broken)
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", _broken)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    headers = {"X-CSRF-Token": token, "Origin": B}
    if json_mode:
        headers["X-Teranga-Mode"] = "json"
    # Message unique à chaque appel : jamais servi depuis le cache des réponses.
    return client.post("/chat", json={"message": message, "language": "fr"}, headers=headers, base_url=B)


def test_fallback_uses_the_place_history_and_access():
    places = app_module.SENEGAL_KNOWLEDGE["places"]
    text = knowledge_fallback("Comment visiter Gorée ?", places)
    assert text.startswith("L'assistant IA est momentanément indisponible")
    assert "Île de Gorée (Dakar)" in text and "Comment y aller : Chaloupe" in text
    assert knowledge_fallback("Quel temps fera-t-il demain ?", places) is None


def test_fallback_knows_dishes():
    text = knowledge_fallback("C'est quoi le yassa ?", [], app_module.SENEGAL_KNOWLEDGE["dishes"])
    assert "Yassa" in text


def test_stream_answers_from_the_knowledge_base_when_the_ai_is_down(monkeypatch):
    response = _post(monkeypatch, "Parle-moi de Gorée, panne stream")
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    assert not any("error" in e for e in events)
    text = "".join(e.get("d", "") for e in events)
    assert "momentanément indisponible" in text and "Gorée" in text
    assert any(e.get("places") for e in events) and events[-1].get("done")


def test_json_mode_answers_from_the_knowledge_base(monkeypatch):
    response = _post(monkeypatch, "Parle-moi de Saint-Louis, panne json", json_mode=True)
    data = response.get_json()
    assert response.status_code == 200 and data["degraded"] is True
    assert "Saint-Louis" in data["reply"]


def test_unknown_topic_still_reports_the_outage(monkeypatch):
    response = _post(monkeypatch, "Quelle heure est-il à Tokyo, panne ?", json_mode=True)
    assert response.status_code == 503 and "error" in response.get_json()


def test_stream_never_ends_with_an_empty_bubble(monkeypatch):
    """Flux sans texte puis réponse complète vide : un message s'affiche quand même."""

    class Empty:
        output_text = ""

    def create_response(payload, stream=False):
        return iter([]) if stream else Empty()

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", create_response)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat", json={"message": "Question sans réponse du modèle 42", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": B}, base_url=B,
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    text = "".join(e.get("d", "") for e in events)
    assert "pas réussi à répondre" in text and events[-1].get("done")
