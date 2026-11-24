"""Page « Mentions légales » (23 novembre 2026).

Journaux Render du 22 au 23 novembre : /mentions-legales et /legal demandés, réponse 404. En France, un site
édité doit afficher son éditeur, son directeur de la publication et son hébergeur (loi pour la confiance dans
l'économie numérique, article 6). Éditeur et contact donnés par le propriétaire le 23 novembre 2026 ; adresse de
l'hébergeur relevée dans les conditions d'utilisation de Render (https://render.com/terms).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app  # noqa: E402

B = "http://localhost"


def _get(path):
    return app.test_client().get(path, base_url=B)


def test_la_page_existe_et_nomme_editeur_directeur_et_hebergeur():
    response = _get("/mentions-legales")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for fait in ("Mentions légales", "Éditeur", "Oumar Ba", "terangaais@gmail.com",
                 "Directeur de la publication", "Hébergeur", "Render Services, Inc.",
                 "525 Brannan Street", "San Francisco", "+1 415 319 8186"):
        assert fait in html, fait
    assert 'href="mailto:terangaais@gmail.com"' in html
    assert 'href="/confidentialite"' in html and 'href="/urgences"' in html


def test_legal_renvoie_vers_les_mentions_legales():
    response = _get("/legal")
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/mentions-legales")


def test_le_pied_de_page_y_mene():
    for path in ("/confidentialite", "/privacy", "/urgences"):
        assert 'href="/mentions-legales"' in _get(path).get_data(as_text=True), path
