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

    # Mode JSON : passe par complete_reply ; aucun appel réseau réel.
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", broken)
    # Depuis le mode autonome branché (always=True), une panne de l'IA reçoit le message honnête de la base du
    # site (200). Le 503 avec Retry-After reste le dernier recours quand même ce secours échoue.
    monkeypatch.setattr("routes.chat.knowledge_fallback", broken)
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


def test_common_url_variants_redirect_to_existing_pages():
    """« / » final, majuscules et alias usuels : redirection 301 au lieu d'une 404."""
    from app import app

    client = app.test_client()
    cases = {
        "/partenaires/": "/partenaires", "/lieux/goree/": "/lieux/goree", "/Dakar": "/dakar",
        "/index.html": "/", "/contact": "/offres-partenaires", "/planificateur": "/trip-planner",
        "/urgence": "/urgences", "/kit-media": "/media-kit", "/en": "/en/senegal-travel-guide",
        "/offres-partenaires/?source=whatsapp": "/offres-partenaires?source=whatsapp",
    }
    for path, target in cases.items():
        response = client.get(path)
        assert response.status_code == 301, path
        assert response.headers["Location"] == target, path
    assert client.get("/mentions-inexistantes").status_code == 404
    assert client.post("/partenaires/").status_code in (404, 405)


def test_redirect_target_never_leaves_the_site():
    from services.error_pages import redirect_target

    always = lambda _path: True  # noqa: E731
    for path in ("//evil.com", "//evil.com/", "///evil.com/x", "/\\evil.com"):
        target = redirect_target(path, always)
        assert target == "" or (target.startswith("/") and not target.startswith("//") and "\\" not in target), (path, target)
    assert redirect_target("/existe-pas/", lambda _path: False) == ""
