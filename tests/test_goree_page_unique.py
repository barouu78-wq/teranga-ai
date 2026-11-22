"""Une seule page Gorée en français : /visiter-goree.

Constat du 22 novembre 2026 : trois pages françaises visaient la même recherche (/visiter-goree, /lieux/goree,
/fr/goree-island) et se faisaient concurrence. /visiter-goree, déjà la page clé (tests/test_pages_cles_seo.py),
devient l'adresse de référence : /fr/goree-island y redirige (301), /lieux/goree reste consultable mais y renvoie sa
canonique, et seules les canoniques restent dans le sitemap. Aucun accès réseau.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest  # noqa: E402

from app import SITE_URL, app  # noqa: E402

B = "https://teranga-ai.fr"
HTML = {"Accept": "text/html"}


@pytest.fixture(scope="module")
def client():
    return app.test_client()


def _get(client, path):
    return client.get(path, base_url=B, headers=HTML, environ_base={"REMOTE_ADDR": "203.0.113.62"})


def _canonical(page):
    found = re.search(r'<link rel="canonical" href="([^"]+)"', page)
    return found and found.group(1)


def test_french_translated_guide_redirects_to_the_french_page(client):
    response = _get(client, "/fr/goree-island")
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/visiter-goree")


def test_place_sheet_stays_readable_but_points_to_the_guide(client):
    response = _get(client, "/lieux/goree")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert _canonical(page) == f"{SITE_URL}/visiter-goree"
    assert 'href="/visiter-goree"' in page


def test_other_place_sheets_keep_their_own_canonical(client):
    page = _get(client, "/lieux/saint-louis").get_data(as_text=True)
    assert _canonical(page) == f"{SITE_URL}/lieux/saint-louis"


def test_sitemap_lists_only_the_canonical_goree_page(client):
    sitemap = _get(client, "/sitemap.xml").get_data(as_text=True)
    assert f"<loc>{SITE_URL}/visiter-goree</loc>" in sitemap
    assert f"<loc>{SITE_URL}/lieux/goree</loc>" not in sitemap
    assert f"<loc>{SITE_URL}/fr/goree-island</loc>" not in sitemap
    assert f"<loc>{SITE_URL}/en/goree-island</loc>" in sitemap


def test_hreflang_links_are_reciprocal(client):
    english = _get(client, "/en/goree-island").get_data(as_text=True)
    assert f'hreflang="fr" href="{SITE_URL}/visiter-goree"' in english
    french = _get(client, "/visiter-goree").get_data(as_text=True)
    for lang in ("en", "es", "de", "it"):
        assert f'hreflang="{lang}" href="{SITE_URL}/{lang}/goree-island"' in french
    assert f'hreflang="fr" href="{SITE_URL}/visiter-goree"' in french


def test_guide_has_practical_content_and_no_placeholder(client):
    page = _get(client, "/visiter-goree").get_data(as_text=True)
    assert "Question type" not in page
    assert "dakargoree.sn" in page
    assert "à vérifier" in page
    # Pas de carte qui renvoie vers la page elle-même.
    assert 'href="/lieux/goree"' not in page


def test_internal_cards_link_to_the_canonical_page(client):
    region = _get(client, "/regions/dakar").get_data(as_text=True)
    assert 'href="/visiter-goree"' in region
    assert 'href="/lieux/goree"' not in region
