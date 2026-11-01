"""Réponses prêtes : les numéros d'urgence servis sans appeler le modèle.

Seulement des repères déjà vérifiés et sourcés du dépôt (routes/emergency.py), et seulement pour une
question courte qui ne demande que ces numéros, en première question, sans lieu ni voyage sélectionné.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import json
from types import SimpleNamespace

import pytest

from services.quick_answers import quick_answer

ASKED = (
    "Numéro d'urgence ?",
    "numeros d urgence au senegal",
    "Quel est le numéro de la police ?",
    "quel est le numero des pompiers a dakar",
    "Numéro du SAMU",
    "Qui appeler en cas d'urgence au Sénégal ?",
    "Les numéros d'urgence s'il te plaît",
)
ASKED_EN = (
    "Emergency numbers in Senegal?",
    "What is the police number?",
    "emergency number",
)
# Une situation, un autre sujet ou une précision : le modèle répond.
NOT_ASKED = (
    "J'ai eu un accident, que faire ?",
    "On m'a volé mon téléphone, quel numéro appeler pour la police ?",
    "Quel est le numéro de SOS Médecins ?",
    "Numéro de la gendarmerie de Mbour",
    "numéro de téléphone de l'hôtel Terrou-Bi",
    "Que visiter à Dakar en deux jours ?",
    "La police est-elle fiable au Sénégal ?",
    "numéro de la police municipale de Thiès pour une plainte",
)


@pytest.mark.parametrize("message", ASKED)
def test_emergency_numbers_question_gets_the_verified_numbers(message):
    answer = quick_answer({"message": message, "language": "fr"}, {"history": [{"role": "user", "content": message}]})
    assert answer is not None
    reply = answer["reply"]
    for number in ("17", "18", "1515"):
        assert number in reply
    assert "même sans crédit" in reply and "teranga-ai.fr/urgences" in reply
    assert answer["sources"] == [{"title": "Ambassade de France au Sénégal", "url": "https://sn.ambafrance.org/Numeros-d-urgence"}]


@pytest.mark.parametrize("message", ASKED_EN)
def test_english_question_gets_the_answer_in_english(message):
    reply = quick_answer({"message": message, "language": "en"}, {})["reply"]
    assert "free from any phone" in reply and "1515" in reply


@pytest.mark.parametrize("message", NOT_ASKED)
def test_other_questions_go_to_the_model(message):
    assert quick_answer({"message": message, "language": "fr"}, {}) is None


def test_only_numbers_already_verified_without_reservation_are_served():
    reply = quick_answer({"message": "numéros d'urgence", "language": "fr"}, {})["reply"]
    # Gendarmerie et SOS Médecins sont à revérifier (décision du propriétaire du 17/10/2026) : pas en réponse prête.
    assert "800 00 20 20" not in reply and "33 889 15 15" not in reply


def test_conversation_context_or_other_languages_go_to_the_model():
    message = "Numéro de la police ?"
    earlier = [{"role": "user", "content": "Je suis à Saint-Louis"}, {"role": "assistant", "content": "Bienvenue !"}]
    assert quick_answer({"message": message, "language": "fr"}, {"history": earlier + [{"role": "user", "content": message}]}) is None
    assert quick_answer({"message": message, "language": "fr"}, {"context_place": "Gorée"}) is None
    assert quick_answer({"message": message, "language": "fr"}, {"trip_context": "Dakar 3 jours"}) is None
    assert quick_answer({"message": message, "language": "wo"}, {}) is None
    assert quick_answer({"message": message, "language": "fr", "photo_only": True}, {}) is None


def test_quick_answer_is_streamed_without_calling_the_model(monkeypatch):
    import app as app_module

    calls = []

    def fake_stream(payload, stream=True):
        calls.append(payload["message"])
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(output_text="modèle"))

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", fake_stream)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat",
        json={"message": "Quel est le numéro de la police ?", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
        base_url="https://teranga-ai.fr",
        environ_base={"REMOTE_ADDR": "203.0.113.171"},
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
    text = "".join(e.get("d", "") for e in events)
    assert calls == [] and "Police secours : 17" in text
    assert any(e.get("done") for e in events)


def _post(client, message, ip):
    token = client.get("/csrf", base_url="https://teranga-ai.fr").get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    return client.post(
        "/chat",
        json={"message": message, "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
        base_url="https://teranga-ai.fr",
        environ_base={"REMOTE_ADDR": ip},
    )


def test_quick_answer_does_not_use_the_web_search_quota():
    import app as app_module

    client = app_module.app.test_client()
    # « urgence » déclenche la recherche web ; la réponse prête n'en fait pas : jamais de refus « trop de recherches ».
    statuses = [_post(client, "Numéros d'urgence ?", "203.0.113.172").status_code for _ in range(12)]
    assert statuses == [200] * 12


def test_quick_answer_wins_over_an_older_model_answer_in_cache(monkeypatch):
    import app as app_module

    old = {"reply": "Gendarmerie : 800 00 20 20, SOS Médecins : 33 889 15 15.", "sources": []}
    monkeypatch.setattr(app_module.ANSWER_CACHE, "get", lambda key: old)
    text = "".join(
        json.loads(line).get("d", "")
        for line in _post(app_module.app.test_client(), "Quel est le numéro de la police ?", "203.0.113.173").get_data(as_text=True).splitlines()
        if line
    )
    assert "Police secours : 17" in text and "800 00 20 20" not in text
