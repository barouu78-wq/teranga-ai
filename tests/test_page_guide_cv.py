"""Page guide « Faire un CV pour le Sénégal » (25 novembre 2026).

Recherches réelles qui ont déclenché l'annonce « CV Sénégal » (Google Ads, 30 jours, via Windsor.ai) : « comment faire
un cv sans expérience professionnelle », « exemple cv étudiant », « comment rédiger un cv », « cv pour stage »,
« créer cv gratuit ». Le site n'avait que l'outil /cv, sans page qui réponde à ces questions. La page reprend les règles
du skill cv-senegal (rien d'inventé) et mène à l'outil gratuit.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app  # noqa: E402
from services.seo import SEO_PAGES  # noqa: E402

B = "http://localhost"
SLUG = "faire-un-cv-senegal"


def _page():
    response = app.test_client().get("/" + SLUG, base_url=B)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_la_page_existe_et_respecte_l_audit_seo():
    assert SLUG in SEO_PAGES
    page = SEO_PAGES[SLUG]
    assert len(page["title"]) <= 65 and "CV" in page["title"]
    assert 70 <= len(page["description"]) <= 165
    assert f"/{SLUG}</loc>" in app.test_client().get("/sitemap.xml", base_url=B).get_data(as_text=True)


def test_la_page_repond_aux_recherches_reelles_et_mene_a_l_outil():
    texte = re.sub(r"<[^>]+>", " ", _page())
    for sujet in ("sans expérience", "étudiant", "stage", "lettre de motivation", "PDF", "gratuit", "n'invente"):
        assert sujet in texte, sujet
    assert 'href="/cv"' in _page()


def test_la_page_n_invente_ni_chiffre_ni_promesse():
    texte = re.sub(r"<[^>]+>", " ", _page())
    assert not re.search(r"\d+\s?%", texte)  # aucune statistique
    assert not re.search(r"\d[\d  .]*\s?(?:€|euros?|F ?CFA|francs)", texte)  # aucun prix
    for promesse in ("garanti", "embauché à coup sûr", "meilleur site"):
        assert promesse not in texte.lower(), promesse
