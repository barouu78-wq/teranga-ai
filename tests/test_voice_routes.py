from app import app


def test_tts_route_points_to_tts_handler():
    rules = [rule for rule in app.url_map.iter_rules() if rule.rule == "/tts"]
    assert len(rules) == 1
    assert rules[0].endpoint == "tts"


def test_stt_rejects_missing_csrf_without_calling_provider():
    client = app.test_client()
    response = client.post("/stt")
    assert response.status_code == 403
    assert response.get_json()["error"] == "csrf"
