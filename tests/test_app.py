import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5.6-luna")

from app import app, lookup_map, should_use_web


def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["model"] == "gpt-5.6-luna"
    assert data["web_search"] is True


def test_current_price_question_uses_web():
    assert should_use_web("Quel est le prix actuel du TER ?") is True


def test_verify_question_uses_web():
    assert should_use_web("Vérifie les horaires actuels") is True


def test_map_for_senegal_city():
    result = lookup_map("Je vais à Ziguinchor")
    assert result is not None
    assert "Ziguinchor" in result["label"]

def test_health_reports_api_key_configured():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["api_key_configured"] is True


def test_referer_origin_is_exact():
    import app as app_module
    with app_module.app.test_request_context(
        "/chat",
        headers={"Referer": "https://teranga-ai-1.onrender.com.evil.example/path"},
    ):
        app_module.ALLOWED_ORIGINS.clear()
        app_module.ALLOWED_ORIGINS.add("https://teranga-ai-1.onrender.com")
        assert app_module.origin_allowed() is False
