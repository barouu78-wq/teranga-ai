"""Bouton « Donner mon avis » : page /avis, envoi, validation et lecture dans la page privée."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402

B = "https://teranga-ai.fr"


def _client(ip):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")

    def post(body, headers=None):
        return client.post("/api/avis", json=body, base_url=B, environ_base={"REMOTE_ADDR": ip},
                           headers={"X-CSRF-Token": token, "Origin": B, **(headers or {})})
    return client, post


def test_page_shows_the_form_and_is_not_indexed():
    response = app_module.app.test_client().get("/avis", base_url=B)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'data-endpoint="/api/avis"' in html and "partner-form.js" in html and 'name="website"' in html
    assert 'name="message"' in html and 'name="kind"' in html
    assert "noindex" in html


def test_footer_and_home_link_to_the_page():
    client = app_module.app.test_client()
    assert 'href="/avis"' in client.get("/offres-partenaires", base_url=B).get_data(as_text=True)
    home = client.get("/", base_url=B).get_data(as_text=True)
    # Propriétaire, 28 novembre 2026 : « Déplace l'avis dans le bas de page ». Plus à côté de « Copier le lien »,
    # mais tout en bas de l'accueil, après les guides (les autres pages l'ont dans leur pied de page).
    start = home.index('<div class="spread">')
    assert "/avis" not in home[start:home.index("</div>", start)]
    assert '<p class="home-foot"><a href="/avis" id="feedbackLink">Donner mon avis</a></p>' in home
    assert home.index('href="/avis"') > home.index('id="guidesTitle"')


def test_feedback_is_validated_stored_and_listed(monkeypatch):
    client, post = _client("203.0.113.91")
    assert post({"kind": "inconnu", "message": "Le micro ne marche pas"}).status_code == 400
    assert post({"kind": "bug", "message": "ok"}).status_code == 400  # message trop court
    ok = post({"kind": "bug", "message": "Le <micro> ne marche pas\nsur mon Samsung", "contact": "", "appli": "1"})
    assert ok.status_code == 200 and ok.get_json() == {"ok": True}
    monkeypatch.setenv("STATS_TOKEN", "x" * 20)
    page = client.post("/stats-partenaires", data={"cle": "x" * 20}, base_url=B,
                       environ_base={"REMOTE_ADDR": "203.0.113.92"}).get_data(as_text=True)
    assert "Avis des utilisateurs" in page
    assert "Le &lt;micro&gt; ne marche pas sur mon Samsung" in page and "Appli Android" in page


def test_feedback_needs_csrf_and_ignores_bots():
    client, post = _client("203.0.113.93")
    denied = client.post("/api/avis", json={"kind": "bug", "message": "Un message assez long"}, base_url=B,
                         headers={"Origin": B}, environ_base={"REMOTE_ADDR": "203.0.113.93"})
    assert denied.status_code == 403
    before = len(app_module.AVIS.recent())
    bot = post({"kind": "idee", "message": "Achetez mes produits", "website": "http://spam"})
    assert bot.status_code == 200 and len(app_module.AVIS.recent()) == before


def test_privacy_page_explains_feedback():
    html = app_module.app.test_client().get("/confidentialite", base_url=B).get_data(as_text=True)
    assert "Avis sur l&#x27;application" in html or "Avis sur l'application" in html
