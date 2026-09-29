from app import app, parse_chat_payload


def test_parse_chat_payload_builds_french_tourist_context():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Je veux visiter Gorée pendant 4 jours avec 100000 FCFA en famille",
            "history": [],
            "language": "fr",
            "audience": "tourist",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["audience"] == "tourist"
    assert payload["planner"] is True
    assert payload["planner_data"]["duration_days"] == 4
    assert payload["planner_data"]["budget_fcfa"] == 100000
    assert "Île de Gorée" in payload["instructions"] or "goree" in payload["context"]["place"]


def test_parse_chat_payload_normalizes_invalid_language_and_audience():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={"message": "Bonjour", "history": [], "language": "xx", "audience": "unknown"},
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["audience"] == "tourist"
    assert "Réponds en français naturel" in payload["instructions"]


def test_parse_chat_payload_rejects_invalid_body():
    with app.test_request_context("/chat", method="POST", data="not-json", content_type="application/json"):
        payload, error = parse_chat_payload()

    assert payload is None
    assert error[1] == 400


def test_parse_chat_payload_makes_photo_only_requests_fast():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={"message": "Montre-moi des photos de Dakar", "history": [], "language": "fr"},
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["intent_context"]["intent"] == "photos"
    assert payload["use_web"] is False
