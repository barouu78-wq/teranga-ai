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
