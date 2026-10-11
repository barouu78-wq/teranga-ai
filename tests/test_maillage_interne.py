"""Maillage interne : chaque page du plan du site doit se trouver en suivant des liens depuis l'accueil.

Un robot découvre surtout les pages en suivant des liens ; le plan du site (sitemap.xml) ne fait que les
lui signaler. Avant ce test, 62 pages sur 200 n'avaient aucun lien depuis l'accueil (les 2 pages
Dakar « visiter-dakar » et « assistant-ia-dakar », et les 60 pages en/es/de/it/fr), et la page des
14 régions ne menait pas aux pages des régions. Aucun accès réseau.
"""

import os
import re
from collections import deque
from urllib.parse import urlparse

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest  # noqa: E402

from app import SITE_URL, app  # noqa: E402

HREF = re.compile(r'<a\b[^>]*\bhref="([^"#]+)"', re.I)
LOC = re.compile(r"<loc>([^<]+)</loc>")
MAX_CLICS = 3


@pytest.fixture(scope="module")
def client():
    return app.test_client()


@pytest.fixture(scope="module")
def sitemap_paths(client):
    body = client.get("/sitemap.xml").get_data(as_text=True)
    return [urlparse(url).path or "/" for url in LOC.findall(body)]


def _internal_links(client, path, cache):
    """Chemins internes (sans paramètres) des liens <a> d'une page."""
    if path not in cache:
        response = client.get(path)
        found = set()
        if response.status_code == 200:
            for href in HREF.findall(response.get_data(as_text=True)):
                if href.startswith(SITE_URL):
                    href = href[len(SITE_URL):] or "/"
                target = urlparse(href).path
                if href.startswith("/") and not href.startswith("//") and target:
                    found.add(target)
        cache[path] = found
    return cache[path]


def test_every_sitemap_page_is_reachable_from_the_home_page_in_three_clicks(client, sitemap_paths):
    cache: dict = {}
    depth = {"/": 0}
    queue = deque(["/"])
    while queue:
        page = queue.popleft()
        if depth[page] == MAX_CLICS:
            continue
        for target in sorted(_internal_links(client, page, cache)):
            if target not in depth:
                depth[target] = depth[page] + 1
                queue.append(target)
    unreachable = [path for path in sitemap_paths if path not in depth]
    assert not unreachable, f"{len(unreachable)} pages du plan du site sans chemin de {MAX_CLICS} clics : {unreachable[:10]}"


def test_regions_page_links_to_the_fourteen_region_pages(client):
    from services.seo import REGION_SEO_NAMES, region_slug

    links = _internal_links(client, "/regions-senegal", {})
    assert len(REGION_SEO_NAMES) == 14
    missing = [name for name in REGION_SEO_NAMES if f"/regions/{region_slug(name)}" not in links]
    assert not missing, f"régions absentes de /regions-senegal : {missing}"


def test_dakar_page_links_to_the_two_dakar_guides_that_had_no_inbound_link(client):
    links = _internal_links(client, "/dakar", {})
    assert {"/visiter-dakar", "/assistant-ia-dakar"} <= links


def test_each_localized_page_links_to_its_translations_and_to_every_other_topic_of_its_language(client):
    from services.international_seo import LANGS, TOPICS

    cache: dict = {}
    for lang in LANGS:
        for topic in TOPICS:
            links = _internal_links(client, f"/{lang}/{topic}", cache)
            translations = {f"/{other}/{topic}" for other in LANGS if other != lang}
            siblings = {f"/{lang}/{other}" for other in TOPICS if other != topic}
            assert translations <= links, (lang, topic, translations - links)
            assert siblings <= links, (lang, topic, siblings - links)


def test_language_switch_marks_each_link_with_its_language(client):
    html = client.get("/es/senegal-visa").get_data(as_text=True)
    switch = re.search(r'<nav class="lang-switch" aria-label="([^"]+)">(.*?)</nav>', html, re.S)
    assert switch and switch.group(1) == "Idiomas"
    assert 'href="/en/senegal-visa" lang="en" hreflang="en">English</a>' in switch.group(2)
    assert 'href="/es/senegal-visa"' not in switch.group(2)  # pas de lien vers la page elle-même
