"""Page « Visa Sénégal » (23 novembre 2026).

Search Console (30 jours, via Windsor.ai) : « visa sénégal pour français » (position 90), « senegal entry visa » (11),
« sénégal digital arrival card » (21,5). /fr/senegal-visa ne disait rien de concret. La nouvelle page ne reprend que
des faits vérifiés : repère « visa » de services/practical_facts.py, faux site de visas (ministère, avril 2026),
carnet de vaccination plus exigé (APS et AllAfrica, 10 mars 2026), et l'absence de source officielle pour une
« carte d'arrivée numérique » proposée par des sites privés.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app import app  # noqa: E402
from services.seo import SEO_PAGES  # noqa: E402

B = "http://localhost"
SLUG = "visa-senegal"


def _page():
    response = app.test_client().get("/" + SLUG, base_url=B)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_la_page_existe_et_respecte_l_audit_seo():
    assert SLUG in SEO_PAGES
    page = SEO_PAGES[SLUG]
    assert len(page["title"]) <= 65 and "Visa" in page["title"]
    assert 70 <= len(page["description"]) <= 165
    assert f"/{SLUG}</loc>" in app.test_client().get("/sitemap.xml", base_url=B).get_data(as_text=True)


def test_l_ancienne_page_francaise_redirige_vers_la_nouvelle():
    response = app.test_client().get("/fr/senegal-visa", base_url=B)
    assert response.status_code == 301 and response.headers["Location"].endswith("/" + SLUG)
    anglais = app.test_client().get("/en/senegal-visa", base_url=B).get_data(as_text=True)
    assert f'hreflang="fr" href="https://teranga-ai.fr/{SLUG}"' in anglais or f'/{SLUG}"' in anglais


def test_la_page_ne_dit_que_des_faits_verifies_avec_leurs_sources():
    html = _page()
    for fait in ("90 jours", "6 mois", "ambassade", "carnet de vaccination", "mars 2026", "avril 2026",
                 "carte d'arrivée numérique", "aucune source officielle", "Sources"):
        assert fait in html, fait
    texte = re.sub(r"<[^>]+>", " ", html)
    # France Diplomatie : passeport valide plus de 6 mois « obligatoire » pour les Français (relecture Codex, PR #661).
    assert "plus de 6 mois est obligatoire" in texte and "France Diplomatie" in texte
    assert "6 mois conseill" not in texte and "6 mois après l'arrivée est conseillée" not in texte
    assert not re.search(r"\d[\d  .]*\s?(?:€|euros?|F ?CFA|francs)", texte)  # aucun prix inventé


def test_les_questions_sur_la_carte_d_arrivee_recoivent_les_reperes_d_entree():
    from services.practical_facts import matching_topics, practical_context as practical_facts

    for question in ("Faut-il une carte d'arrivée numérique pour le Sénégal ?", "senegal digital arrival card",
                     "SNDAC Senegal obligatoire ?", "fiche d'arrivée en ligne pour Dakar"):
        assert "visa" in matching_topics(question), question
    assert "aucune source officielle" in practical_facts("senegal digital arrival card")
    # Pas de faux déclenchement : une carte bancaire ou l'heure d'arrivée d'un vol ne sont pas l'entrée au pays.
    for question in ("ma carte bancaire marche à Dakar ?", "à quelle heure arrive le vol de Paris ?"):
        assert "visa" not in matching_topics(question), question
