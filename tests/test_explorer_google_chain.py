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


def test_explorer_uses_wikipedia_article_photos_when_google_finds_nothing():
    app = Flask(__name__)
    calls = []

    def article(title, limit=4):
        calls.append(("article", title))
        # « Île de Saint-Louis » n'a pas d'article : le nom court « Saint-Louis » en a un.
        return [{"url": "https://upload.wikimedia.org/sl.jpg", "display_url": "/image-proxy?url=sl"}] if title == "Saint-Louis" else []

    def google(query, limit=4):
        calls.append(("google", query))
        return []

    register_explorer_routes(
        app, {"places": [], "regions": [{"name": "Dakar"}]}, google, lambda q, limit=4: [], lambda url: "/p",
        fetch_article_images=article,
    )
    data = app.test_client().get("/explorer-image?query=Île Saint-Louis Sénégal&title=Île de Saint-Louis").get_json()
    assert data["images"][0]["url"].endswith("sl.jpg")
    # Google d'abord, puis l'article du lieu (nom complet, puis nom court).
    assert calls == [("google", "Île Saint-Louis Sénégal"), ("article", "Île de Saint-Louis"), ("article", "Saint-Louis")]


def test_article_titles_skip_a_short_name_that_is_a_whole_region():
    from routes.explorer import article_titles

    assert article_titles("Corniche de Dakar", ["Dakar"]) == ["Corniche de Dakar"]
    assert article_titles("Lac Rose / Lac Retba") == ["Lac Rose"]
    assert article_titles("") == []


def test_explorer_cards_show_french_type_and_send_the_place_name():
    from app import app as main_app

    html = main_app.test_client().get("/explorer").get_data(as_text=True)
    assert "Patrimoine · Dakar" in html and "heritage ·" not in html
    assert 'data-title="Île de Gorée"' in html and "&title='" in html


def _knowledge():
    return {
        "regions": [{"name": "Diourbel"}],
        "places": [{"id": "touba", "name": "Touba", "image_queries": ["Touba Sénégal Grande Mosquée", "Grande Mosquée de Touba"]}],
    }


def test_commons_tries_the_other_queries_of_the_place():
    app = Flask(__name__)
    calls = []

    def commons(query, limit=4):
        calls.append(query)
        return [{"url": "https://upload.wikimedia.org/touba.jpg"}] if query == "Grande Mosquée de Touba" else []

    register_explorer_routes(app, _knowledge(), lambda q, limit=4: [], commons, lambda url: "/p?u=" + url,
                             fetch_article_images=lambda t, limit=4: [])
    data = app.test_client().get("/explorer-image?query=Touba Sénégal Grande Mosquée&title=Touba").get_json()
    assert data["images"][0]["display_url"] == "/p?u=https://upload.wikimedia.org/touba.jpg"
    assert calls == ["Touba Sénégal Grande Mosquée", "Grande Mosquée de Touba"]


def test_no_photo_is_remembered_briefly_to_save_the_google_quota():
    app = Flask(__name__)
    calls = []

    def google(query, limit=4):
        calls.append(query)
        return []

    register_explorer_routes(app, {"places": [], "regions": []}, google, lambda q, limit=4: [], lambda url: "/p")
    client = app.test_client()
    client.get("/explorer-image?query=Rien")
    client.get("/explorer-image?query=Rien")
    assert calls == ["Rien"]


def test_found_photos_are_shared_through_redis():
    class FakeRedis:
        def __init__(self):
            self.store = {}

        def get(self, key):
            return self.store.get(key)

        def setex(self, key, ttl, value):
            self.store[key] = value

    redis = FakeRedis()
    calls = []

    def google(query, limit=4):
        calls.append(query)
        return [{"url": "https://example.com/a.jpg", "display_url": "https://example.com/a.jpg"}]

    first, second = Flask("w1"), Flask("w2")  # deux workers Gunicorn
    for flask_app in (first, second):
        register_explorer_routes(flask_app, {"places": [], "regions": []}, google, lambda q, limit=4: [], lambda url: "/p", redis_client=redis)
    first.test_client().get("/explorer-image?query=Goree")
    data = second.test_client().get("/explorer-image?query=Goree").get_json()
    assert data["images"][0]["url"] == "https://example.com/a.jpg" and calls == ["Goree"]


def test_article_images_try_the_short_title_when_the_first_request_fails():
    import io
    import json as _json

    from services.images import fetch_article_images

    requested = []
    payload = {"query": {"pages": {"1": {"title": "Fichier:Touba.jpg", "imageinfo": [{
        "mime": "image/jpeg", "width": 1600, "height": 1000, "url": "https://upload.wikimedia.org/t.jpg",
        "thumburl": "https://upload.wikimedia.org/t.jpg", "extmetadata": {}}]}}}}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(req, timeout=5):
        requested.append(req.full_url)
        if "Touba_test%20%28S%C3%A9n%C3%A9gal%29" in req.full_url or "Touba_test+%28S%C3%A9n%C3%A9gal%29" in req.full_url:
            raise OSError("panne passagère")
        return Resp(_json.dumps(payload).encode())

    photos = fetch_article_images("Touba_test", urlopen_fn=opener)
    assert len(requested) == 2 and photos and photos[0]["url"].endswith("t.jpg")
