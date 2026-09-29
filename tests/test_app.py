import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5.6-luna")

# Garantit que l'application à la racine du dépôt est importable quel que soit le mode pytest.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import env_bool
from app import SENEGAL_KNOWLEDGE, app, fetch_commons_image, fetch_topic_images, image_proxy_url, lookup_map, model_kwargs, public_error, should_use_web



def test_env_bool_accepts_common_true_values(monkeypatch):
    for value in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert env_bool("TEST_BOOL", False) is True


def test_env_bool_accepts_common_false_values(monkeypatch):
    for value in ("0", "false", "FALSE", "no", "off", ""):
        monkeypatch.setenv("TEST_BOOL", value)
        assert env_bool("TEST_BOOL", True) is False


def test_env_bool_uses_default_for_unknown_values(monkeypatch):
    monkeypatch.setenv("TEST_BOOL", "maybe")
    assert env_bool("TEST_BOOL", True) is True
    assert env_bool("TEST_BOOL", False) is False


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

def test_responses_include_request_id_header():
    client = app.test_client()
    first = client.get("/health")
    second = client.get("/health")
    assert first.status_code == 200
    assert second.status_code == 200
    first_id = first.headers.get("X-Request-ID")
    second_id = second.headers.get("X-Request-ID")
    assert first_id
    assert second_id
    assert len(first_id) == 16
    assert len(second_id) == 16
    assert first_id != second_id


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


def test_photo_request_prefers_google_images_and_returns_multiple(monkeypatch):
    import app as app_module

    google_calls = []
    def fake_google(title, limit=4):
        google_calls.append((title, limit))
        return [
            {"url": f"https://images.example/{i}.jpg", "alt": f"Dakar {i}", "credit": "Google Images"}
            for i in range(8)
        ]

    monkeypatch.setattr(app_module, "fetch_google_images", fake_google)
    monkeypatch.setattr(app_module, "fetch_commons_images", lambda *args, **kwargs: [])
    monkeypatch.setattr(app_module, "fetch_city_image", lambda title: None)
    monkeypatch.setattr(app_module, "topic_wikipedia_titles", lambda message, limit=4: [])

    images = app_module.fetch_topic_images("Montre-moi des photos de Dakar")
    assert len(images) == 8
    assert google_calls == [("Dakar", 8)]
    assert all(item["credit"] == "Google Images" for item in images)


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
    assert calls[0][1] == 4
    assert images[0]["display_url"].startswith("/image-proxy?url=")


def test_photo_request_handles_goree_typo_without_falling_back_to_dakar(monkeypatch):
    import app as app_module

    calls = []

    def fake_commons(title, limit=4):
        calls.append(title)
        return [{
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Goree.jpg",
            "alt": "Île de Gorée",
            "credit": "Wikimédia Commons",
        }] if "Gorée" in title else []

    monkeypatch.setattr(app_module, "fetch_commons_images", fake_commons)
    monkeypatch.setattr(
        app_module,
        "knowledge_image_titles",
        lambda message, limit=4: (_ for _ in ()).throw(AssertionError("fallback Dakar should not be used")),
    )
    monkeypatch.setattr(app_module, "topic_wikipedia_titles", lambda message, limit=4: [])

    images = app_module.fetch_topic_images("Montre-moi les photo de gore")
    assert images
    assert all("Gorée" in title for title in calls)
    assert not any("Dakar" in title for title in calls)


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



def test_visual_requests_trigger_web_search_first():
    assert should_use_web("Montre-moi des photos de Gorée") is True
    assert should_use_web("À quoi ressemble ce lieu ?") is True


def test_visual_system_rule_requires_web_before_requesting_user_photo():
    import app as app_module
    assert "tente d'abord une recherche web" in app_module.SYSTEM_PROMPT
    assert "Ne demande une photo à l'utilisateur qu'après cette recherche" in app_module.SYSTEM_PROMPT


def test_responses_include_response_time_header():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    value = response.headers.get("X-Response-Time-ms")
    assert value
    assert float(value) >= 0


def test_stt_uses_centralized_csrf_validation(monkeypatch):
    import io
    import app as app_module
    from types import SimpleNamespace

    monkeypatch.setattr(
        app_module.client.audio.transcriptions,
        "create",
        lambda **kwargs: SimpleNamespace(text="bonjour"),
    )
    client = app.test_client()
    csrf = client.get("/csrf")
    token = csrf.get_json()["token"]
    response = client.post(
        "/stt",
        data={"audio": (io.BytesIO(b"fake-audio"), "voice.webm"), "language": "fr"},
        headers={
            "Origin": app_module.SITE_URL,
            "X-CSRF-Token": token,
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["text"] == "bonjour"


def test_system_prompt_uses_structured_knowledge_without_embedded_catalogue():
    import app as app_module

    assert "base structurée" in app_module.SYSTEM_PROMPT
    assert "Figures historiques" not in app_module.SYSTEM_PROMPT
    assert "14 régions" not in app_module.SYSTEM_PROMPT
    assert len(app_module.SYSTEM_PROMPT) < 7000
    assert app_module.SENEGAL_PEOPLE

def test_system_routes_expose_expected_contracts():
    client = app.test_client()

    health = client.get("/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok", "service": "teranga-ai"}

    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.content_type.startswith("application/manifest+json")
    assert manifest.get_json()["start_url"] == "/"


def test_explorer_image_requires_a_query():
    client = app.test_client()
    response = client.get("/explorer-image")
    assert response.status_code == 200
    assert response.get_json() == {"images": []}


def test_explorer_page_renders():
    client = app.test_client()
    response = client.get("/explorer")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert "Teranga AI" in response.get_data(as_text=True)


def test_indexnow_key_is_served():
    client = app.test_client()
    key = "8078ffb659c643b58bddddca48be0627"

    response = client.get(f"/{key}.txt")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == key
    assert response.content_type.startswith("text/plain")


def test_public_seo_pages_expose_native_share_control():
    from services.seo import render_seo_page
    body=render_seo_page("dakar","https://example.com").get_data(as_text=True)
    assert 'id="share-page"' in body
    assert "navigator.share" in body
    assert "navigator.clipboard.writeText(location.href)" in body


def test_regional_seo_page_and_sitemap():
    client = app.test_client()
    response = client.get("/regions/dakar")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Région Dakar" in body
    assert 'rel="canonical"' in body
    assert "/regions/dakar" in body
    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/regions/dakar" in sitemap


def test_trip_planner_carries_explicit_audience_into_prompt():
    from services.trip_planner import _prompt

    data = {
        "lang": "fr",
        "arrival": "2026-10-01",
        "departure": "2026-10-04",
        "adults": 2,
        "children": 0,
        "interests": ["Culture & histoire"],
        "budget": "Confort",
        "pace": "Équilibré",
        "regions": ["Dakar"],
        "audience": "diaspora",
        "context_place": "Gorée",
        "surprise": False,
    }
    prompt = _prompt(data)
    assert "User profile: diaspora" in prompt
    assert "explicit preference" in prompt


def test_trip_planner_page_reads_and_shares_audience_profile():
    client = app.test_client()
    response = client.get("/trip-planner?lang=fr&audience=diaspora")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "teranga-audience" in body
    assert "audienceQuery" in body
    assert "audience:audience" in body


def test_home_chat_includes_adjust_planner_action():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)

    assert "Ajuster dans le Planner" in html
    assert "teranga-trip-context" in html


def test_home_consumes_planner_chat_prefill():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)

    assert "teranga-chat-prefill" in html
    assert "input.value=prefill" in html


def test_home_captures_explicit_trip_edit_request():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)

    assert "detectTripEditRequest" in html
    assert "teranga-trip-edit-proposal" in html




def test_explorer_image_gallery_has_direct_fallback():
    from app import app

    html = app.test_client().get("/explorer").get_data(as_text=True)

    assert "dataset.directUrl" in html
    assert "fallbackUsed" in html
    assert "track.appendChild(img)" in html


def test_home_has_narrow_mobile_layout_rules():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)

    assert "@media(max-width:520px)" in html
    assert ".spread{display:grid;grid-template-columns:1fr;gap:7px}" in html


def test_trip_planner_has_mobile_action_layout():
    from app import app

    html = app.test_client().get("/trip-planner?lang=fr").get_data(as_text=True)

    assert "@media(max-width:560px)" in html
    assert ".actions{flex-direction:column}" in html


def test_explorer_has_mobile_tap_targets():
    from app import app

    html = app.test_client().get("/explorer").get_data(as_text=True)

    assert "article>a{display:block" in html
    assert "min-height:40px" in html


def test_home_bounds_persisted_chat_history():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)

    assert "slice(0,1200)" in html
    assert "version:1" in html
    assert "safeHistory" in html



def test_home_audience_buttons_bind_directly():
    from app import app

    html = app.test_client().get("/").get_data(as_text=True)

    assert "document.querySelectorAll('.audience-btn').forEach" in html
    assert "['tourist','resident','diaspora','merchant']" in html
    assert "diaspora:{" in html
    assert "resident:{" in html
