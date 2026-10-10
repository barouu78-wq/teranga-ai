"""Une question autonome ne reprend pas l'intention, la recherche web ni le raisonnement du fil.

Les corps de requête reproduisent static/home.js : la question courante est déjà le dernier
élément de ``history`` au moment de l'envoi. Seul un vrai suivi (« Et demain ? », « Combien ça
coûte ? », « Précise ») reprend le sujet précédent.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

import app as app_module
from services.intelligence import build_intent_context


def turn(role, content):
    return {"role": role, "content": content}


def parse(message, history=()):
    body = {"message": message, "history": [*history, turn("user", message)], "language": "fr", "audience": "tourist"}
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def fake_forecast(monkeypatch):
    """Météo en direct simulée, avec la même condition que la vraie (intention « weather »)."""
    fetched = []

    def fake(locations, intent_context, message, *args, **kwargs):
        if (intent_context or {}).get("intent") != "weather":
            return None
        fetched.append(message)
        return "PRÉVISIONS SIMULÉES"

    monkeypatch.setattr(app_module, "live_weather_context", fake)
    return fetched


WEATHER = [turn("user", "Quelle météo à Dakar aujourd'hui ?"), turn("assistant", "Ciel dégagé, environ 31 degrés.")]
PHOTOS = [turn("user", "Montre-moi des photos de Gorée"), turn("assistant", "Voici des photos de Gorée.")]
PRICE = [
    turn("user", "Quel est le prix du taxi de l'aéroport ?"),
    turn("assistant", "Entre 15 000 et 20 000 FCFA, à vérifier."),
]
WHY = [turn("user", "Pourquoi le lac Rose est-il rose ?"), turn("assistant", "À cause d'algues.")]
PLAN = [
    turn("user", "Planifie un séjour de 5 jours à Saint-Louis avec 300000 FCFA en famille"),
    turn("assistant", "Jour 1 : arrivée à Saint-Louis."),
]


# --- Intention : météo ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("question", [
    "Quel est le prix du ferry pour Gorée ?",
    "Quels sont les horaires de la Maison des Esclaves ?",
    "Quelle langue parle-t-on au Sénégal ?",
])
def test_standalone_question_after_weather_is_not_a_weather_question(monkeypatch, question):
    fetched = fake_forecast(monkeypatch)
    payload = parse(question, WEATHER)
    assert payload["intent_context"]["intent"] == "general_information"
    assert payload["intent_context"]["domain"] != "weather"
    assert fetched == [] and not payload.get("live_weather") and "PRÉVISIONS" not in payload["instructions"]


def test_price_and_hours_questions_keep_their_web_search_after_weather(monkeypatch):
    """La prévision injectée supprimait la recherche web de la question de prix ou d'horaires."""
    fake_forecast(monkeypatch)
    assert parse("Quel est le prix du ferry pour Gorée ?", WEATHER)["use_web"] is True
    assert parse("Quels sont les horaires de la Maison des Esclaves ?", WEATHER)["use_web"] is True


@pytest.mark.parametrize("follow_up", ["et demain ?", "Et à Saint-Louis ?", "Et pour ce week-end ?", "Demain ?", "Précise"])
def test_elliptical_follow_up_still_continues_the_weather_question(monkeypatch, follow_up):
    fetched = fake_forecast(monkeypatch)
    payload = parse(follow_up, WEATHER)
    assert payload["intent_context"]["intent"] == "weather"
    assert fetched == [follow_up] and payload["live_weather"] is True


def test_follow_up_with_its_own_intent_keeps_it(monkeypatch):
    fetched = fake_forecast(monkeypatch)
    payload = parse("Et où manger à Dakar ?", WEATHER)
    assert payload["intent_context"]["intent"] == "restaurant" and fetched == []


# --- Intention : photos ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("question", [
    "Quelle est la meilleure saison pour y aller ?",
    "Quels sont les horaires de la Maison des Esclaves ?",
    "Quelle langue parle-t-on au Sénégal ?",
])
def test_standalone_question_after_photos_does_not_ask_for_images(question):
    assert parse(question, PHOTOS)["intent_context"]["needs_images"] is False


def test_elliptical_follow_up_after_photos_still_asks_for_images():
    for follow_up in ("Et à Saint-Louis ?", "Encore", "Une autre ?"):
        assert parse(follow_up, PHOTOS)["intent_context"]["needs_images"] is True, follow_up


# --- Recherche web --------------------------------------------------------------------------------------------


def test_unrelated_question_after_a_price_question_does_not_search_the_web():
    assert parse("Quelle langue parle-t-on au Sénégal ?", PRICE)["use_web"] is False
    assert parse("Que veut dire teranga ?", PRICE)["use_web"] is False


@pytest.mark.parametrize("follow_up", ["et en bus ?", "Combien ça coûte ?", "Et pour les enfants ?", "Précise"])
def test_follow_up_after_a_price_question_still_searches_the_web(follow_up):
    assert parse(follow_up, PRICE)["use_web"] is True


# --- Raisonnement approfondi ---------------------------------------------------------------------------------


def test_unrelated_question_after_a_why_question_stays_on_the_fast_model():
    assert parse("Quelle langue parle-t-on au Sénégal ?", WHY)["deep_reasoning"] is False
    assert parse("Que veut dire teranga ?", PLAN)["deep_reasoning"] is False


def test_follow_up_after_a_why_question_keeps_the_deep_reasoning():
    assert parse("et à Dakar ?", WHY)["deep_reasoning"] is True


def test_standalone_question_with_its_own_constraints_is_still_deep():
    payload = parse("Je veux lancer un petit commerce avec 150000 FCFA et trouver mes premiers clients.", WEATHER)
    assert payload["deep_reasoning"] is True


def test_plan_iteration_keeps_the_planning_mode():
    """Le planificateur ne dépend pas de la forme du message : on itère sur un plan en cours."""
    assert parse("Mets plutôt 3 jours", PLAN)["planner"] is True


# --- Unités ----------------------------------------------------------------------------------------------------


def test_intent_context_units():
    weather = [turn("user", "Quelle météo à Dakar ?")]
    assert build_intent_context("Et demain ?", weather)["intent"] == "weather"
    assert build_intent_context("Et pour le budget ?", [turn("user", "Je veux lancer un commerce à Dakar.")])["intent"] == "project"
    assert build_intent_context("Quelle langue parle-t-on au Sénégal ?", weather)["intent"] == "general_information"
    assert build_intent_context("Quelle langue parle-t-on au Sénégal ?", weather)["needs_web_search"] is False
