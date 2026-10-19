"""Teranga répond seul aux conversions euro ↔ FCFA, sans appeler le modèle.

Décision du propriétaire du 19 octobre 2026 : donner plus d'indépendance à Teranga en servant lui-même les questions
fréquentes qu'il sait déjà traiter avec ses données vérifiées. Le franc CFA est à parité fixe avec l'euro
(1 € = 655,957 FCFA) : le calcul est fait par services/calculators.py, jamais par le modèle. Le dollar, la livre, une
question avec un contexte ou une précision vont toujours au modèle.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import json
from types import SimpleNamespace

import pytest

from services.quick_answers import quick_answer

ASKED = (
    ("100 euros en FCFA ?", "100 € = 65 595,70 FCFA"),
    ("100 € en cfa", "100 € = 65 595,70 FCFA"),
    ("Combien font 50 000 FCFA en euros", "50 000 FCFA = 76,22 €"),
    ("convertir 250 euros", "250 € = 163 989,25 FCFA"),
    ("1 euro = combien de francs CFA", "1 € = 655,96 FCFA"),
    ("combien de FCFA pour 20 euros ?", "20 € = 13 119,14 FCFA"),
)
# Une autre devise (taux variable), une situation, un contexte ou un calcul de commerçant : le modèle répond.
NOT_ASKED = (
    "100 dollars en FCFA",
    "50 livres en FCFA",
    "Un hôtel à 50 000 FCFA la nuit, c'est cher ?",
    "100 euros en FCFA pour payer mon loyer à Dakar ?",
    "J'achète à 1 000 FCFA et je vends à 1 500 FCFA, quelle marge ?",
    "Comment envoyer 100 euros au Sénégal ?",
    "Que visiter à Dakar ?",
    "euros",
)


def _ask(message, language="fr", raw=None):
    return quick_answer({"message": message, "language": language}, raw or {})


@pytest.mark.parametrize("message, line", ASKED)
def test_conversion_question_gets_the_calculated_answer(message, line):
    answer = _ask(message)
    assert answer is not None, message
    reply = answer["reply"]
    assert line in reply
    assert "1 € = 655,957 FCFA" in reply and "fixe" in reply
    # Pas de trace du format interne destiné au modèle.
    assert "CALCUL VÉRIFIÉ" not in reply and "recopier" not in reply


@pytest.mark.parametrize("message", NOT_ASKED)
def test_other_questions_go_to_the_model(message):
    assert _ask(message) is None


def test_context_history_and_other_languages_go_to_the_model():
    message = "100 euros en FCFA ?"
    earlier = [{"role": "user", "content": "Je pars à Saly"}, {"role": "assistant", "content": "Bon voyage !"}]
    assert _ask(message, raw={"history": earlier + [{"role": "user", "content": message}]}) is None
    assert _ask(message, raw={"trip_context": "Saly 3 jours"}) is None
    assert _ask(message, raw={"context_place": "Gorée"}) is None
    assert _ask(message, language="wo") is None
    # L'anglais garde le modèle (avec le bloc de calcul vérifié) : les nombres seraient au format français.
    assert _ask(message, language="en") is None


def test_emergency_numbers_are_still_served():
    assert "1515" in _ask("Numéro du SAMU")["reply"]


def test_conversion_is_streamed_without_calling_the_model(monkeypatch):
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
        json={"message": "100 euros en FCFA ?", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": "https://teranga-ai.fr"},
        base_url="https://teranga-ai.fr",
        environ_base={"REMOTE_ADDR": "203.0.113.181"},
    )
    events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
    text = "".join(e.get("d", "") for e in events)
    assert calls == [] and "100 € = 65 595,70 FCFA" in text
    assert any(e.get("done") for e in events)
