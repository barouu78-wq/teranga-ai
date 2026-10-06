from pathlib import Path


HOME = Path(__file__).resolve().parents[1] / "templates" / "home.html"
IMAGES = Path(__file__).resolve().parents[1] / "services" / "images.py"


def test_explorer_prefers_wikimedia_thumbnail_for_fast_loading():
    source = IMAGES.read_text(encoding="utf-8")
    assert 'info.get("thumburl") or info.get("url")' in source


def test_visible_language_selector_excludes_pulaar():
    html = HOME.read_text(encoding="utf-8")
    assert 'data-lang="ff">PU' not in html
    assert 'data-lang="fr"' in html
    assert 'data-lang="en"' in html
    assert 'data-lang="wo"' in html


def test_explorer_uses_google_images_before_wikimedia_fallback():
    from flask import Flask

    from routes.explorer import register_explorer_routes

    calls = []

    def google(query, limit=4):
        calls.append(("google", query, limit))
        return []

    def commons(query, limit=4):
        calls.append(("commons", query, limit))
        return [{"url": "https://upload.wikimedia.org/x.jpg"}]

    app = Flask(__name__)
    register_explorer_routes(app, {"places": [], "regions": []}, google, commons, lambda url: "/p")
    assert app.test_client().get("/explorer-image?query=Goree").get_json()["images"]
    assert calls == [("google", "Goree", 4), ("commons", "Goree", 4)]


def test_explorer_gallery_query_is_not_double_encoded():
    from services.explorer import render_explorer_page

    html = render_explorer_page([{"id": "goree", "name": "Île de Gorée", "region": "Dakar", "image_queries": ["Île de Gorée Sénégal"]}], [], "")
    assert 'data-query="Île de Gorée Sénégal"' in html
    assert "%C3%8E" not in html.split('data-query="', 1)[1].split('"', 1)[0]


def test_explorer_image_falls_back_to_commons_when_google_fails():
    from flask import Flask

    from routes.explorer import register_explorer_routes

    def google(query, limit=4):
        raise RuntimeError("HTTP 403")

    app = Flask(__name__)
    register_explorer_routes(
        app, {"places": [], "regions": []}, google,
        lambda query, limit=4: [{"url": "https://upload.wikimedia.org/g.jpg"}],
        lambda url: "/image-proxy?url=" + url,
    )
    data = app.test_client().get("/explorer-image?query=Gor%C3%A9e").get_json()
    assert data["images"][0]["display_url"] == "/image-proxy?url=https://upload.wikimedia.org/g.jpg"
