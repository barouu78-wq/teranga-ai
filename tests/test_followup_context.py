"""Contexte de suivi : un remerciement ne relance rien, et la question garde son propre domaine.

Les corps de requête reproduisent static/home.js : la question courante est déjà le dernier
élément de ``history`` au moment de l'envoi.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

import app as app_module
from services.intelligence import build_intent_context, is_acknowledgement


def turn(role, content):
    return {"role": role, "content": content}


def parse(message, history=()):
    body = {
        "message": message,
        "history": [*history, turn("user", message)],
        "language": "fr",
        "audience": "tourist",
    }
    with app_module.app.test_request_context("/chat", method="POST", json=body):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def model_of(payload):
    return app_module._CHAT_SERVICE["model_kwargs"](payload, False)["model"]


PLAN = [
    turn("user", "Planifie un séjour de 5 jours à Saint-Louis avec 300000 FCFA en famille"),
    turn("assistant", "Jour 1 : arrivée à Saint-Louis et visite de l'île."),
]
WEATHER = [turn("user", "Quelle météo à Dakar aujourd'hui ?"), turn("assistant", "Ciel dégagé, environ 31 degrés.")]
PRICE = [
    turn("user", "Quel est le prix du taxi de l'aéroport ?"),
    turn("assistant", "Entre 15 000 et 20 000 FCFA, à vérifier."),
]
PHOTOS = [turn("user", "Montre-moi des photos de Gorée"), turn("assistant", "Voici des photos de Gorée.")]


def fake_forecast(monkeypatch):
    """Remplace la météo en direct par un faux qui respecte la même condition (intention « weather »)."""
    fetched = []

    def fake(locations, intent_context, message, *args, **kwargs):
        if (intent_context or {}).get("intent") != "weather":
            return None
        fetched.append(message)
        return "PRÉVISIONS SIMULÉES"

    monkeypatch.setattr(app_module, "live_weather_context", fake)
    return fetched


# --- Remerciements et adieux ----------------------------------------------------------------------------------


@pytest.mark.parametrize("message", [
    "merci", "Merci !", "merci beaucoup", "Merci bien.", "merci 🙏", "mille mercis", "Un grand merci",
    "super, merci", "Parfait merci", "thanks", "Thank you so much", "Jërëjëf", "A jaraama",
    "au revoir", "À bientôt", "Bonne journée !", "bye",
])
def test_thanks_and_goodbyes_are_acknowledgements(message):
    assert is_acknowledgement(message)


@pytest.mark.parametrize("message", [
    "", "ok", "oui", "continue", "vas-y",
    "oui merci",  # accepte une proposition
    "non merci",  # refuse une proposition
    "merci, et combien coûte le taxi ?",
    "Merci de vérifier les horaires du ferry",
    "Quelle est la capitale du Sénégal ?",
    "Et demain ?",
])
def test_requests_and_answers_to_an_offer_are_not_acknowledgements(message):
    assert not is_acknowledgement(message)


def test_thanks_after_a_trip_request_does_not_restart_the_plan():
    payload = parse("merci", PLAN)
    assert payload["planner"] is False and payload["deep_reasoning"] is False
    assert "MODE PLANIFICATION ACTIF" not in payload["instructions"]
    assert model_of(payload) == "gpt-5.6-luna"
    # Le modèle reçoit quand même la conversation pour répondre naturellement.
    assert "Saint-Louis" in payload["input_text"] and "<demande_utilisateur>\nmerci" in payload["input_text"]


def test_thanks_after_a_price_question_does_not_search_the_web():
    assert parse("Quel est le prix du taxi ?", PRICE)["use_web"] is True  # la vraie question, elle, cherche
    assert parse("merci", PRICE)["use_web"] is False


def test_thanks_after_a_weather_question_does_not_fetch_a_forecast(monkeypatch):
    fetched = fake_forecast(monkeypatch)
    payload = parse("merci", WEATHER)
    assert fetched == [] and not payload.get("live_weather")
    assert payload["intent_context"]["intent"] == "general_information"
    assert "PRÉVISIONS" not in payload["instructions"]


def test_thanks_after_photos_does_not_ask_for_images():
    assert parse("merci", PHOTOS)["intent_context"]["needs_images"] is False


def test_a_real_follow_up_still_inherits_the_previous_topic(monkeypatch):
    fetched = fake_forecast(monkeypatch)
    payload = parse("et demain ?", WEATHER)
    assert payload["intent_context"]["intent"] == "weather" and fetched == ["et demain ?"]
    assert payload["live_weather"] is True
    assert parse("et en bus ?", PRICE)["use_web"] is True


def test_thanks_keeps_the_conversation_for_the_model_but_not_its_constraints():
    payload = parse("merci", PLAN)
    assert payload["context"]["constraints"] == [] and payload["intent_context"]["memory"].get("budget") is None


# --- Domaine : la question parle de son propre sujet --------------------------------------------------------


def test_question_domain_wins_over_an_older_topic():
    # Une question qui a son propre sujet reçoit le domaine qu'elle aurait en première question.
    after_weather = build_intent_context("Où manger à Dakar ?", WEATHER)
    assert after_weather["intent"] == "restaurant"
    assert after_weather["domain"] == build_intent_context("Où manger à Dakar ?")["domain"] != "weather"
    after_price = build_intent_context("Raconte l'histoire de la ville de Saint-Louis", PRICE)
    assert after_price["domain"] == "culture"


def test_follow_up_without_its_own_topic_keeps_the_conversation_domain():
    assert build_intent_context("Et demain ?", WEATHER)["domain"] == "weather"
    # Un suivi dont l'intention est reprise du fil garde le domaine du fil, même s'il cite un autre mot.
    assert build_intent_context("Et pour la plage ?", WEATHER)["domain"] == "weather"


def test_restaurant_question_after_weather_is_not_limited_to_the_weather_agency():
    payload = parse("Où manger à Dakar ?", WEATHER)
    assert payload["use_web"] is True
    tool = app_module._CHAT_SERVICE["model_kwargs"](payload, False)["tools"][0]
    assert "anacim.sn" not in tool.get("filters", {}).get("allowed_domains", [])
