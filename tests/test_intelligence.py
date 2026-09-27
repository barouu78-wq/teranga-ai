from services.intelligence import (
    build_intent_context,
    detect_intent,
    detect_location,
    detect_language,
)


def test_trip_planning_context():
    result = build_intent_context(
        "Je pars à Dakar vendredi, fais-moi un itinéraire de 4 jours."
    )
    assert result["intent"] == "trip_planning"
    assert result["location"] == "dakar"
    assert result["needs_web_search"] is True
    assert result["needs_images"] is False


def test_goree_photo_context():
    result = build_intent_context("Montre-moi les photos de Gorée.")
    assert result["intent"] == "photos"
    assert result["location"] == "goree"
    assert result["needs_images"] is True


def test_weather_context():
    assert detect_intent("Quelle météo à Dakar demain ?") == "weather"
    assert detect_location("Quelle météo à Dakar demain ?") == "dakar"


def test_language_contract():
    assert detect_language("Bonjour, je veux visiter Dakar") == "fr"
    assert detect_language("Hello, I want to travel to Dakar") == "en"


def test_context_history_is_flagged_without_changing_query():
    result = build_intent_context(
        "Et demain ?",
        history=[{"role": "user", "content": "Je suis à Dakar"}],
    )
    assert result["has_context"] is True
    assert result["query"] == "Et demain ?"
