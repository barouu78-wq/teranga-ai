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
    assert "Île de Gorée" in payload["instructions"]
    assert "Repère fourni par l’interface" in payload["instructions"] or "goree" in payload["context"]["place"]


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


def test_parse_chat_payload_combines_local_knowledge_with_fresh_web_policy():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Quel est le prix actuel pour visiter Gorée ?",
            "history": [],
            "language": "fr",
            "audience": "tourist",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["use_web"] is True
    assert "Île de Gorée" in payload["instructions"]
    assert "COMBINAISON CONNAISSANCE + WEB" in payload["instructions"]
    assert "informations susceptibles d’avoir changé" in payload["instructions"]


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



def test_parse_chat_payload_makes_natural_photo_request_fast():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={"message": "Des photo Île de Gorée", "history": [], "language": "fr"},
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["use_web"] is False


def test_parse_chat_payload_uses_selected_place_context_for_follow_up():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Que faire ici demain ?",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "context_place": "Île de Gorée",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["context"]["place"] == "Île de Gorée"
    assert payload["context"]["has_place"] is True
    assert "Île de Gorée" in payload["contextual_query"]
    assert "Île de Gorée" in payload["instructions"]

def test_parse_chat_payload_uses_compact_trip_context():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Peux-tu ajuster ce séjour ?",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "trip_context": '{"summary":"Séjour Dakar et Gorée","days":[{"day":1,"region":"Dakar","title":"Plateau"},{"day":2,"region":"Dakar","title":"Gorée"}]}',
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert "Contexte d’itinéraire fourni par l’interface" in payload["instructions"]
    assert "Séjour Dakar et Gorée" in payload["instructions"]


def test_parse_chat_payload_limits_trip_context():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={"message": "Ajuste mon séjour", "trip_context": "x" * 3000},
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert len(payload["trip_context"]) == 1600



def test_parse_chat_payload_preserves_bounded_trip_edit_request():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Remplace le jour 2 par Saint-Louis",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "trip_edit_request": "Remplace le jour 2 par Saint-Louis",
        },
    ):
        payload, error = parse_chat_payload()
    assert error is None
    assert payload["trip_edit_request"] == "Remplace le jour 2 par Saint-Louis"


def test_parse_chat_payload_accepts_region_with_followup_text():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Remplace le jour 2 par Saint-Louis, s'il te plaît",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "trip_context": '{"summary":"Séjour Sénégal","days":[{"day":1,"region":"Dakar"},{"day":2,"region":"Dakar"}]}',
            "trip_edit_request": "Remplace le jour 2 par Saint-Louis, s'il te plaît",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["trip_edit_proposal"]["region"] == "Saint-Louis"


def test_parse_chat_payload_rejects_out_of_range_trip_edit_day():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Remplace le jour 99 par Saint-Louis",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "trip_context": '{"summary":"Séjour Sénégal","days":[{"day":1,"region":"Dakar"}]}',
            "trip_edit_request": "Remplace le jour 99 par Saint-Louis",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["trip_edit_proposal"] is None


def test_parse_chat_payload_caps_trip_edit_request():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "change le jour 2",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "trip_edit_request": "x" * 900,
        },
    ):
        payload, error = parse_chat_payload()
    assert error is None
    assert len(payload["trip_edit_request"]) == 500


def test_parse_chat_payload_builds_confirmed_day_region_proposal():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Remplace le jour 2 par Saint-Louis",
            "history": [],
            "language": "fr",
            "audience": "tourist",
            "trip_context": '{"summary":"Séjour Sénégal","days":[{"day":1,"region":"Dakar"},{"day":2,"region":"Dakar"}]}',
            "trip_edit_request": "Remplace le jour 2 par Saint-Louis",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["trip_edit_proposal"] == {
        "action": "replace_day_region",
        "day": 2,
        "region": "Saint-Louis",
        "requires_confirmation": True,
    }


def test_parse_chat_payload_follow_up_keeps_weather_source_policy():
    with app.test_request_context(
        "/chat",
        method="POST",
        json={
            "message": "Et demain ?",
            "history": [{"role": "user", "content": "Quelle météo à Dakar aujourd'hui ?"}],
            "language": "fr",
            "audience": "tourist",
        },
    ):
        payload, error = parse_chat_payload()

    assert error is None
    assert payload["use_web"] is True
    assert payload["intent_context"]["domain"] == "weather"
    assert payload["intent_context"]["preferred_sources"][:2] == ("meteofrance.com", "ansd.sn")
