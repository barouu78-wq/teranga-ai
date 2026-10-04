"""Pages d'erreur : 404 aux couleurs du site, suggestions de lieux, 503 pour l'IA."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

B = "https://teranga-ai.fr"


def _client():
    from app import app

    return app.test_client()


def test_unknown_page_is_a_branded_noindex_404():
    response = _client().get("/nexiste-pas", base_url=B, headers={"Accept": "text/html"})
    html = response.get_data(as_text=True)
    assert response.status_code == 404
    assert 'content="noindex"' in html and "Page introuvable" in html and 'href="/lieux"' in html


def test_mistyped_place_suggests_the_closest_pages():
    html = _client().get("/lieux/gore", base_url=B, headers={"Accept": "text/html"}).get_data(as_text=True)
    assert 'href="/lieux/goree"' in html


def test_api_404_stays_json():
    response = _client().get("/api/inexistant", base_url=B)
    assert response.status_code == 404 and response.is_json


def test_ai_failure_in_json_mode_is_503_with_retry_after(monkeypatch):
    import app as app_module

    def broken(*_args, **_kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", broken)
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    response = client.post(
        "/chat",
        json={"message": "Bonjour", "language": "fr"},
        headers={"X-CSRF-Token": token, "Origin": B, "X-Teranga-Mode": "json"},
        base_url=B,
    )
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "10"
    assert "inaccessible" in response.get_json()["error"]
