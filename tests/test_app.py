import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5.6-luna")

# Garantit que l'application à la racine du dépôt est importable quel que soit le mode pytest.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

    original_origins = set(app_module.ALLOWED_ORIGINS)
    try:
        app_module.ALLOWED_ORIGINS.clear()
        app_module.ALLOWED_ORIGINS.add("https://teranga-ai-1.onrender.com")
        with app_module.app.test_request_context(
            "/chat",
            headers={"Referer": "https://teranga-ai-1.onrender.com.evil.example/path"},
        ):
            assert app_module.origin_allowed() is False
    finally:
        app_module.ALLOWED_ORIGINS.clear()
        app_module.ALLOWED_ORIGINS.update(original_origins)
