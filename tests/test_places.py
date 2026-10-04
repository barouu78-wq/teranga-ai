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
