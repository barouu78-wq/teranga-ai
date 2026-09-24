import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5.6-luna")

# Garantit que l'application à la racine du dépôt est importable quel que soit le mode pytest.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app, lookup_map, public_error, should_use_web


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


def test_seo_pages_and_sitemap():
    client = app.test_client()
    for path in (
        "/senegal",
        "/meteo-dakar",
        "/visiter-goree",
        "/restaurants-dakar",
        "/specialites-senegal",
        "/regions-senegal",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert "Teranga AI" in response.get_data(as_text=True)
    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/meteo-dakar" in sitemap
    assert "/regions-senegal" in sitemap


def test_security_headers():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_chat_requires_csrf_and_json():
    client = app.test_client()
    response = client.post("/chat", data="{}", content_type="text/plain")
    assert response.status_code == 415

    csrf = client.get("/csrf")
    assert csrf.status_code == 200
    token = csrf.get_json()["token"]
    response = client.post(
        "/chat",
        json={"message": "Bonjour", "history": [], "language": "fr"},
        headers={"X-CSRF-Token": "invalid"},
    )
    assert response.status_code == 403


def test_health_does_not_expose_secret():
    client = app.test_client()
    body = client.get("/health").get_data(as_text=True)
    assert os.environ["OPENAI_API_KEY"] not in body
    assert "SECRET_KEY" not in body


def test_public_error_classifies_auth_and_bad_request():
    assert "OPENAI_API_KEY" in public_error(Exception("401 invalid api key"))
    assert "requête IA" in public_error(Exception("BadRequestError invalid parameter"))


def test_public_error_classifies_model_error():
    assert "modèle IA" in public_error(Exception("model gpt-x not available"))
