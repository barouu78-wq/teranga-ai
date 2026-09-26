import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5.6-luna")

# Garantit que l'application à la racine du dépôt est importable quel que soit le mode pytest.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import SENEGAL_KNOWLEDGE, app, fetch_commons_image, fetch_topic_images, image_proxy_url, lookup_map, model_kwargs, public_error, should_use_web



def test_senegal_knowledge_is_multisource():
    scope = SENEGAL_KNOWLEDGE["knowledge_scope"]
    domains = scope["domains"]
    assert "weather_climate" in domains
    assert "health" in domains
    assert "mobility" in domains
    assert "economy" in domains
    assert "culture_history" in domains
    assert "daily_life" in domains
    source_names = {source["name"] for source in SENEGAL_KNOWLEDGE["source_registry"]}
    assert {"ANSD", "ANACIM", "Ministère de la Santé et de l’Hygiène publique", "UNESCO"} <= source_names


def test_senegal_knowledge_covers_all_fourteen_regions():
    assert len(SENEGAL_KNOWLEDGE["regions"]) == 14
    assert len({region["name"] for region in SENEGAL_KNOWLEDGE["regions"]}) == 14

def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "model" not in data
    assert "api_key_configured" not in data


def test_current_price_question_uses_web():
    assert should_use_web("Quel est le prix actuel du TER ?") is True


def test_verify_question_uses_web():
    assert should_use_web("Vérifie les horaires actuels") is True


def test_map_for_senegal_city():
    result = lookup_map("Je vais à Ziguinchor")
    assert result is not None
    assert "Ziguinchor" in result["label"]


def test_health_does_not_expose_configuration_details():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert "api_key_configured" not in data
    assert "model" not in data


def test_image_redirect_target_is_restricted():
    import app as app_module

    assert app_module._allowed_image_url("https://upload.wikimedia.org/wikipedia/commons/a/a0/test.jpg")
    assert app_module._allowed_image_url("https://thumb.wikimedia.org/wikipedia/commons/a/a0/test.jpg")
    assert not app_module._allowed_image_url("http://upload.wikimedia.org/wikipedia/commons/a/a0/test.jpg")
    assert not app_module._allowed_image_url("https://example.com/test.jpg")
    assert not app_module._allowed_image_url("https://upload.wikimedia.org@evil.example/test.jpg")
    assert not app_module._allowed_image_url("https://upload.wikimedia.org:8443/test.jpg")


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


def test_commons_image_lookup_returns_real_wikimedia_url(monkeypatch):
    import app as app_module
    import io
    import json

    payload = {
        "query": {
            "pages": {
                "1": {
                    "title": "File:Dakar.jpg",
                    "imageinfo": [{
                        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Dakar.jpg/900px-Dakar.jpg",
                        "url": "https://upload.wikimedia.org/wikipedia/commons/d/d1/Dakar.jpg",
                        "extmetadata": {"ImageDescription": {"value": "Vue de Dakar"}},
                    }],
                }
            }
        }
    }

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(
        app_module,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(json.dumps(payload).encode("utf-8")),
    )
    result = fetch_commons_image("Dakar")
    assert result["url"].startswith("https://upload.wikimedia.org/")
    assert result["credit"] == "Wikimédia Commons"
    assert result["alt"] == "Vue de Dakar"


def test_photo_request_routes_to_wikimedia_image(monkeypatch):
    import app as app_module

    calls = []

    def fake_fetch(title):
        calls.append(title)
        return {
            "url": "https://upload.wikimedia.org/wikipedia/commons/d/d1/Dakar.jpg",
            "alt": "Vue de Dakar",
            "credit": "Wikimédia Commons",
        }

    monkeypatch.setattr(app_module, "fetch_commons_images", lambda title, limit=2: [])
    monkeypatch.setattr(app_module, "fetch_city_image", fake_fetch)
    monkeypatch.setattr(app_module, "topic_wikipedia_titles", lambda message, limit=4: [])

    images = fetch_topic_images("Montre-moi des photos de Dakar")
    assert images
    assert images[0]["url"].startswith("https://upload.wikimedia.org/")
    assert "Dakar" in calls[0]


def test_photo_request_prioritizes_exact_place_commons_search(monkeypatch):
    import app as app_module

    calls = []

    def fake_commons(title, limit=4):
        calls.append((title, limit))
        if "Gorée" in title:
            return [{
                "url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Goree.jpg",
                "alt": "Île de Gorée",
                "credit": "Wikimédia Commons",
            }]
        return []

    monkeypatch.setattr(app_module, "fetch_commons_images", fake_commons)
    monkeypatch.setattr(app_module, "topic_wikipedia_titles", lambda message, limit=4: [])
    monkeypatch.setattr(app_module, "knowledge_image_titles", lambda message, limit=4: ["Dakar"])

    images = fetch_topic_images("Montre-moi des photos de Gorée")
    assert images
    assert "Gorée" in calls[0][0]
    assert calls[0][1] == 2
    assert images[0]["display_url"].startswith("/image-proxy?url=")


def test_commons_images_include_same_origin_proxy(monkeypatch):
    import app as app_module
    import io
    import json

    payload = {
        "query": {
            "pages": {
                "1": {
                    "title": "File:Gorée.jpg",
                    "imageinfo": [{
                        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Goree.jpg/960px-Goree.jpg",
                        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Goree.jpg",
                        "mime": "image/jpeg",
                        "thumbmime": "image/jpeg",
                        "extmetadata": {},
                    }],
                }
            }
        }
    }

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(
        app_module,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(json.dumps(payload).encode("utf-8")),
    )
    images = app_module.fetch_commons_images("Île de Gorée Sénégal", limit=1)
    assert images
    assert images[0]["display_url"].startswith("/image-proxy?url=")


def test_model_uses_configured_low_reasoning_for_fast_chat():
    payload = {
        "instructions": "test",
        "input_text": "Bonjour",
        "use_web": False,
        "message": "Bonjour",
    }
    kwargs = model_kwargs(payload, stream=True)
    assert kwargs["reasoning"] == {"effort": "low"}


def test_image_proxy_allows_wikimedia_and_blocks_other_hosts(monkeypatch):
    import app as app_module
    import io

    class FakeResponse(io.BytesIO):
        def __init__(self):
            super().__init__(b"fake-image")
            self.headers = {"Content-Type": "image/jpeg"}
        def get_content_type(self):
            return self.headers["Content-Type"]
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(app_module._SAFE_IMAGE_OPENER, "open", lambda *args, **kwargs: FakeResponse())
    client = app.test_client()

    good = client.get("/image-proxy?url=https%3A%2F%2Fupload.wikimedia.org%2Fwikipedia%2Fcommons%2Fd%2Fd1%2FDakar.jpg")
    assert good.status_code == 200
    assert good.content_type == "image/jpeg"
    assert good.data == b"fake-image"

    bad = client.get("/image-proxy?url=https%3A%2F%2Fevil.example%2Fimage.jpg")
    assert bad.status_code == 400


def test_image_proxy_url_is_same_origin():
    assert image_proxy_url("https://upload.wikimedia.org/wikipedia/commons/d/d1/Dakar.jpg").startswith("/image-proxy?url=")


def test_photo_request_continues_after_wikimedia_lookup_error(monkeypatch):
    import app as app_module

    calls = []

    def fake_fetch(title):
        calls.append(title)
        if title == "Dakar":
            raise RuntimeError("Commons indisponible")
        return {
            "url": "https://upload.wikimedia.org/wikipedia/commons/d/d1/Dakar.jpg",
            "alt": "Vue de Dakar",
            "credit": "Wikimédia Commons",
        }

    monkeypatch.setattr(app_module, "fetch_commons_images", lambda title, limit=2: [])
    monkeypatch.setattr(app_module, "knowledge_image_titles", lambda message, limit=4: ["Dakar", "Gorée"])
    monkeypatch.setattr(app_module, "topic_wikipedia_titles", lambda message, limit=4: [])
    monkeypatch.setattr(app_module, "fetch_city_image", fake_fetch)

    images = app_module.fetch_topic_images("Montre-moi des photos de Dakar")
    assert images
    assert calls == ["Dakar", "Gorée"]
    assert images[0]["credit"] == "Wikimédia Commons"


def test_image_proxy_rejects_google_thumbnail_hosts():
    client = app.test_client()
    response = client.get(
        "/image-proxy?url=https%3A%2F%2Fencrypted-tbn0.gstatic.com%2Fimages%3Fq%3Dtest"
    )
    assert response.status_code == 400


def test_international_travel_seo_pages_cover_all_localized_routes():
    client = app.test_client()
    from services.international_seo import LANGS, TOPICS

    assert len(LANGS) == 5
    assert len(TOPICS) == 12

    for lang in LANGS:
        for topic in TOPICS:
            response = client.get(f"/{lang}/{topic}")
            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert '<link rel="canonical"' in body
            assert 'hreflang="x-default"' in body
            assert "Practical focus" in body or "Enfoque práctico" in body or "Praktischer Fokus" in body or "Focus pratico" in body or "Focus pratique" in body

    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    assert sitemap.count("<loc>") >= 1 + len(TOPICS) * len(LANGS)
    assert "/en/senegal-travel-guide" in sitemap
    assert "/fr/senegal-trip-planner" in sitemap


def test_language_quality_contract_covers_all_supported_languages():
    from services.language_quality import LANGUAGE_RULES, language_instruction

    assert set(LANGUAGE_RULES) == {"fr", "en", "wo", "ff"}
    for language in ("fr", "en", "wo", "ff"):
        instruction = language_instruction(language)
        assert "LANGUE DE SORTIE" in instruction
        assert len(instruction) > 180


def test_language_quality_contract_has_specific_safety_for_wolof_and_pulaar():
    from services.language_quality import language_instruction

    wolof = language_instruction("wo").lower()
    pulaar = language_instruction("ff").lower()
    assert "n'invente" in wolof
    assert "n'invente" in pulaar
    assert "traduction littérale" in wolof
    assert "traduction littérale" in pulaar
