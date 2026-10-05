import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.places import render_place_page


def test_every_place_has_a_page_and_is_in_sitemap():
    from app import SENEGAL_KNOWLEDGE, app

    client = app.test_client()
    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/lieux</loc>" in sitemap
    for place in SENEGAL_KNOWLEDGE["places"]:
        response = client.get(f"/lieux/{place['id']}")
        assert response.status_code == 200, place["id"]
        assert f"/lieux/{place['id']}</loc>" in sitemap
    index = client.get("/lieux").get_data(as_text=True)
    assert "Île de Gorée" in index and 'href="/lieux/goree"' in index


def test_unknown_place_is_404():
    from app import app

    assert app.test_client().get("/lieux/inconnu").status_code == 404


def test_place_page_content_and_csp_nonce():
    from app import app

    response = app.test_client().get("/lieux/goree")
    html = response.get_data(as_text=True)
    assert "<h1>Île de Gorée</h1>" in html
    assert '"@type": "TouristAttraction"' in html and '"GeoCoordinates"' in html
    assert "openstreetmap.org/export/embed.html" in html
    assert 'href="/?q=Parle-moi%20de%20%C3%8Ele%20de%20Gor%C3%A9e"' in html
    csp = response.headers["Content-Security-Policy"]
    nonce = csp.split("'nonce-", 1)[1].split("'", 1)[0]
    assert f'<script nonce="{nonce}">' in html


def test_place_page_escapes_data():
    place = {"id": "x", "name": '<img src=x onerror=alert(1)>', "region": "Dakar", "summary": '"quoted"', "history": "<b>h</b>"}
    html = render_place_page(place, [place], "https://teranga-ai.fr")
    assert "<img src=x" not in html and "<b>h</b>" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_explorer_cards_link_to_place_pages():
    from app import app

    assert 'href="/lieux/goree"' in app.test_client().get("/explorer").get_data(as_text=True)


def test_place_page_shows_how_to_get_there():
    from app import app

    html = app.test_client().get("/lieux/goree").get_data(as_text=True)
    assert "Comment y aller" in html and "gare maritime" in html


def test_place_aliases_find_the_place_and_its_photos(monkeypatch):
    import app as app_module
    from services.senegal_knowledge import format_senegal_knowledge

    context = format_senegal_knowledge(app_module.SENEGAL_KNOWLEDGE, query="Tell me about Pink Lake")
    assert "- Lac Rose / Lac Retba" in context

    calls = []

    def fake_commons(title, limit=4):
        calls.append(title)
        return [{"url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Retba.jpg", "alt": "Lac Rose", "credit": "Wikimédia Commons"}]

    monkeypatch.setattr(app_module, "fetch_commons_images", fake_commons)
    monkeypatch.setattr(app_module, "topic_wikipedia_titles", lambda message, limit=4: [])
    monkeypatch.setattr(
        app_module, "knowledge_image_titles",
        lambda message, limit=4: (_ for _ in ()).throw(AssertionError("le lieu doit être reconnu par son autre nom")),
    )
    assert app_module.fetch_topic_images("Show me photos of Pink Lake")
    assert calls and all("Lac Rose" in title or "Retba" in title for title in calls)
