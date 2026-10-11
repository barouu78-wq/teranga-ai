"""Pages clés du référencement : chaque adresse attendue répond 200 avec le bon contenu.

Constat du 11 octobre 2026 : `/assistant-senegal` et `/dakar` répondent 200, mais `/meteo` et `/goree`
(adresses courtes, sans page propre) renvoyaient la page « Erreur 404 — Page introuvable ». Les vraies pages
sont `/meteo-dakar` et `/visiter-goree` : les adresses courtes y redirigent désormais en 301, ce qui regroupe
les signaux de référencement sur une seule adresse. Aucun accès réseau.
"""

import html as html_lib
import os
import re
from urllib.parse import urlparse

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest  # noqa: E402

from app import SITE_URL, app  # noqa: E402

B = "https://teranga-ai.fr"
HTML = {"Accept": "text/html"}
PAGES = {
    "/assistant-senegal": "Assistant Sénégal",
    "/dakar": "Dakar",
    "/meteo-dakar": "Météo Dakar",
    "/visiter-goree": "Visiter l'île de Gorée",
}
SHORT_ADDRESSES = {"/meteo": "/meteo-dakar", "/goree": "/visiter-goree"}
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
HREF = re.compile(r'<a\b[^>]*\bhref="([^"]+)"', re.I)
LOC = re.compile(r"<loc>([^<]+)</loc>")


@pytest.fixture(scope="module")
def client():
    return app.test_client()


def _h1(page_html):
    found = H1.findall(page_html)
    assert len(found) == 1, f"{len(found)} balises <h1>"
    return html_lib.unescape(re.sub(r"<[^>]+>", "", found[0])).strip()


def _path(url):
    return urlparse(url).path or "/"


@pytest.mark.parametrize("path,title", PAGES.items())
def test_each_key_page_answers_200_with_its_own_content(client, path, title):
    response = client.get(path, base_url=B, headers=HTML)
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert _h1(page) == title
    assert "Page introuvable" not in page
    # Canonique : l'adresse elle-même, sur le domaine principal, indexable.
    assert f'<link rel="canonical" href="{SITE_URL}{path}">' in page
    robots = re.search(r'<meta name="robots" content="([^"]+)"', page)
    assert robots and "noindex" not in robots.group(1)


@pytest.mark.parametrize("short,target", SHORT_ADDRESSES.items())
def test_short_address_redirects_permanently_to_the_real_page(client, short, target):
    response = client.get(short, base_url=B, headers=HTML, follow_redirects=False)
    assert response.status_code == 301
    assert _path(response.headers["Location"]) == target


@pytest.mark.parametrize("short,target", SHORT_ADDRESSES.items())
def test_short_address_ends_on_the_real_page_with_its_content(client, short, target):
    response = client.get(short, base_url=B, headers=HTML, follow_redirects=True)
    assert response.status_code == 200
    assert _h1(response.get_data(as_text=True)) == PAGES[target]


def test_redirect_keeps_the_query_string_and_ignores_the_case(client):
    response = client.get("/MeTeO?utm_source=google", base_url=B, headers=HTML, follow_redirects=False)
    assert response.status_code == 301
    location = urlparse(response.headers["Location"])
    assert (location.path, location.query) == ("/meteo-dakar", "utm_source=google")
    assert client.get("/GOREE", base_url=B, headers=HTML).status_code == 301


def test_an_unknown_address_is_still_a_noindex_404(client):
    # Les alias ne doivent pas avaler toutes les adresses voisines.
    for path in ("/meteo-inconnu", "/goree-inconnue", "/assistant-inconnu"):
        response = client.get(path, base_url=B, headers=HTML)
        assert response.status_code == 404, path
        assert 'content="noindex"' in response.get_data(as_text=True), path


def test_sitemap_lists_the_real_pages_and_not_the_short_addresses(client):
    body = client.get("/sitemap.xml", base_url=B).get_data(as_text=True)
    locs = LOC.findall(body)
    paths = {_path(url) for url in locs}
    assert set(PAGES) <= paths, set(PAGES) - paths
    assert not set(SHORT_ADDRESSES) & paths
    # Chaque adresse du plan du site est sur le domaine principal.
    assert all(url.startswith(SITE_URL + "/") or url == SITE_URL for url in locs)


def test_no_internal_link_points_to_a_short_address(client):
    for page_path in ["/", *PAGES]:
        page = client.get(page_path, base_url=B, headers=HTML).get_data(as_text=True)
        targets = {_path(href) for href in HREF.findall(page) if href.startswith(("/", SITE_URL))}
        bad = targets & set(SHORT_ADDRESSES)
        assert not bad, f"{page_path} lie vers {bad}"


def _internal_targets(client, page_path):
    page = client.get(page_path, base_url=B, headers=HTML).get_data(as_text=True)
    return {_path(href) for href in HREF.findall(page) if href.startswith(("/", SITE_URL))}


def test_home_page_links_to_each_real_page(client):
    """Les pages réelles sont à un clic de l'accueil : un robot les trouve en suivant des liens."""
    assert set(PAGES) <= _internal_targets(client, "/")


def test_dakar_page_links_to_the_weather_and_gorée_pages(client):
    assert {"/meteo-dakar", "/visiter-goree"} <= _internal_targets(client, "/dakar")
