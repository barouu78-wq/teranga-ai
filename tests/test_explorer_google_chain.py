from flask import Flask

from routes.explorer import register_explorer_routes


def test_explorer_returns_google_images_without_fallback():
    app = Flask(__name__)
    calls = []

    def google(query, limit=4):
        calls.append("google")
        return [{"url": "https://example.com/original.jpg", "display_url": "https://example.com/thumb.jpg"}]

    def commons(query, limit=4):
        calls.append("commons")
        return [{"url": "https://upload.wikimedia.org/example.jpg"}]

    register_explorer_routes(app, {"places": [], "regions": []}, google, commons, lambda url: "/image-proxy")
    response = app.test_client().get("/explorer-image?query=Dindefello")

    assert response.status_code == 200
    assert response.get_json()["images"][0]["display_url"] == "https://example.com/thumb.jpg"
    assert calls == ["google"]


def test_explorer_falls_back_to_commons_when_google_returns_nothing():
    app = Flask(__name__)
    calls = []

    def google(query, limit=4):
        calls.append("google")
        return []

    def commons(query, limit=4):
        calls.append("commons")
        return [{"url": "https://upload.wikimedia.org/example.jpg"}]

    register_explorer_routes(app, {"places": [], "regions": []}, google, commons, lambda url: "/image-proxy?url=encoded")
    response = app.test_client().get("/explorer-image?query=Dindefello")

    assert response.status_code == 200
    assert response.get_json()["images"][0]["display_url"] == "/image-proxy?url=encoded"
    assert calls == ["google", "commons"]
