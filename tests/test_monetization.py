"""Revenus : liens affiliés (/go), adresses partenaires, page des offres."""

import datetime as dt
import os
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services.monetization import (  # noqa: E402
    affiliate_config,
    affiliate_target,
    booking_html,
    booking_links,
    partners_context,
    partners_for_place,
    partners_for_text,
    partners_html,
)

B = "https://teranga-ai.fr"
GOREE = {"id": "goree", "name": "Île de Gorée", "region": "Dakar", "locality": "Dakar"}
PARTNER = {
    "id": "hotel-test", "name": "Hôtel de la Plage", "category": "Hôtel", "description": "Face à la mer.",
    "places": ["goree", "Saint-Louis"], "url": "https://hotel.example/", "phone": "+221 33 000 00 00",
}


def _client():
    from app import app

    return app.test_client()


def test_affiliate_ids_are_validated():
    config = affiliate_config({"GETYOURGUIDE_PARTNER_ID": "ABC123", "BOOKING_AID": "bad id<script>"})
    assert config == {"activites": "ABC123"}
    assert affiliate_config({}) == {}


def test_targets_stay_on_partner_hosts_even_with_a_url_as_query():
    config = {"activites": "ABC123", "hotels": "999"}
    target = urlparse(affiliate_target("activites", "https://evil.example/x", config))
    assert target.netloc == "www.getyourguide.com" and parse_qs(target.query)["partner_id"] == ["ABC123"]
    hotel = urlparse(affiliate_target("hotels", "Dakar, Sénégal", config))
    assert hotel.netloc == "www.booking.com" and parse_qs(hotel.query) == {"ss": ["Dakar, Sénégal"], "aid": ["999"]}
    assert affiliate_target("autre", "Dakar", config) is None
    assert affiliate_target("hotels", "  ", config) is None


def test_go_redirects_only_when_configured(monkeypatch):
    monkeypatch.delenv("BOOKING_AID", raising=False)
    assert _client().get("/go/hotels?q=Dakar", base_url=B).status_code == 404
    monkeypatch.setenv("BOOKING_AID", "123456")
    response = _client().get("/go/hotels?q=Dakar&from=goree", base_url=B)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://www.booking.com/searchresults.html?")
    assert "aid=123456" in response.headers["Location"]
    # Jamais servie depuis un cache : chaque clic atteint le serveur et est compté.
    assert "public" not in response.headers["Cache-Control"] and "noindex" in response.headers["X-Robots-Tag"]


def test_booking_links_point_to_go_and_page_shows_disclosure(monkeypatch):
    links = booking_links(GOREE, {"activites": "A1", "hotels": "H1"})
    assert [link["kind"] for link in links] == ["hotels", "activites"]
    assert all(link["href"].startswith("/go/") for link in links)
    html = booking_html(links)
    assert 'rel="sponsored nofollow"' in html and "commission" in html

    monkeypatch.delenv("GETYOURGUIDE_PARTNER_ID", raising=False)
    monkeypatch.delenv("BOOKING_AID", raising=False)
    assert "Réserver" not in _client().get("/lieux/goree", base_url=B).get_data(as_text=True)
    monkeypatch.setenv("GETYOURGUIDE_PARTNER_ID", "A1")
    page = _client().get("/lieux/goree", base_url=B).get_data(as_text=True)
    assert "<h2>Réserver</h2>" in page and "/go/activites?" in page and "commission" in page


def test_partners_are_matched_labelled_and_expire():
    today = dt.date(2026, 10, 5)
    assert partners_for_place([PARTNER], GOREE, today) == [PARTNER]
    assert partners_for_place([PARTNER], {"id": "touba", "region": "Diourbel"}, today) == []
    expired = {**PARTNER, "until": "2026-01-01"}
    assert partners_for_place([expired], GOREE, today) == []
    assert partners_for_text([PARTNER], "Où dormir à Saint-Louis ?", today) == [PARTNER]
    assert partners_for_text([PARTNER], "Bonjour", today) == []

    html = partners_html([PARTNER])
    assert "Partenaire" in html and 'rel="sponsored noopener"' in html and "Devenir partenaire" in html
    unsafe = partners_html([{**PARTNER, "url": "javascript:alert(1)", "name": "<b>x</b>"}])
    assert "javascript:" not in unsafe and "<b>x</b>" not in unsafe
    assert "partenaire de Teranga AI" in partners_context([PARTNER])


def test_chat_context_names_partners_as_partners(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "PARTNERS", [PARTNER])
    with app_module.app.test_request_context("/chat", method="POST", json={"message": "Où dormir à Saint-Louis ?", "language": "fr"}):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    assert "ADRESSES PARTENAIRES" in payload["instructions"] and "Hôtel de la Plage" in payload["instructions"]


def test_chat_place_links_carry_booking_links_when_configured(monkeypatch):
    import app as app_module

    monkeypatch.setenv("BOOKING_AID", "H1")
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", lambda payload: ("Gorée est une île.", [], None, None))
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    data = client.post(
        "/chat",
        json={"message": "Parle-moi de Gorée", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": B, "X-Teranga-Mode": "json"},
        base_url=B,
    ).get_json()
    assert data["places"][0]["id"] == "goree"
    assert data["places"][0]["book"][0]["href"].startswith("/go/hotels?")


def test_offers_page_robots_and_sitemap(monkeypatch):
    monkeypatch.setenv("CONTACT_EMAIL", "contact@teranga-ai.fr")
    client = _client()
    html = client.get("/offres-partenaires", base_url=B).get_data(as_text=True)
    assert "Devenir partenaire" in html and "mailto:contact@teranga-ai.fr" in html and "Partenaire" in html
    assert "Disallow: /go/" in client.get("/robots.txt", base_url=B).get_data(as_text=True)
    assert "/offres-partenaires</loc>" in client.get("/sitemap.xml", base_url=B).get_data(as_text=True)
