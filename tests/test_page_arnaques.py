"""Page « Arnaques Wave et Orange Money au Sénégal » (23 novembre 2026).

Search Console (30 derniers jours, lu via Windsor.ai) : les sujets forts de Teranga (arnaques, mobile money,
démarches) n'apparaissaient jamais dans Google, faute de page dédiée. Cette page reprend les repères déjà vérifiés de
services/practical_facts.py (sujets « arnaques » et « mobile_money ») : aucun fait, montant ni numéro nouveau.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app  # noqa: E402
from services.seo import SEO_PAGES  # noqa: E402

SLUG = "arnaques-mobile-money-senegal"


def _page():
    response = app.test_client().get("/" + SLUG)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_la_page_existe_et_est_dans_le_plan_du_site():
    assert SLUG in SEO_PAGES
    sitemap = app.test_client().get("/sitemap.xml").get_data(as_text=True)
    assert f"/{SLUG}</loc>" in sitemap


def test_titre_et_description_respectent_l_audit_seo():
    page = SEO_PAGES[SLUG]
    assert len(page["title"]) <= 65 and "Wave" in page["title"] and "Orange Money" in page["title"]
    assert 70 <= len(page["description"]) <= 165


def test_la_page_reprend_les_reperes_verifies():
    html = _page()
    for fait in ("code secret", "code reçu par SMS", "par erreur", "Division spéciale de cybersécurité",
                 "BCEAO", "ARTP", "carte professionnelle", "17", "Yas", "faux SMS"):
        assert fait in html, fait


def test_aucun_montant_ni_numero_invente():
    """Les repères ne citent ni frais, ni plafond, ni numéro d'opérateur : la page non plus."""
    texte = re.sub(r"<[^>]+>", " ", _page())
    assert not re.search(r"\d[\d  .]*\s?(?:F ?CFA|francs)", texte)
    assert not re.search(r"(?<!\d)(?:33|7[05678])[ .]?\d{3}[ .]?\d{2}[ .]?\d{2}(?!\d)", texte)


def test_la_page_cite_ses_sources_et_renvoie_aux_urgences():
    html = _page()
    assert "Sources" in html and "Police nationale" in html and "Trésor public" in html
    assert 'href="/urgences"' in html
