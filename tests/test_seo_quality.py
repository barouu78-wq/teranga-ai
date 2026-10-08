"""Qualité SEO de toutes les pages du sitemap : titre, description, données structurées, contenu."""

import html
import json
import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

B = "https://teranga-ai.fr"


def _client():
    from app import app

    return app.test_client()


def _sitemap_paths(client):
    xml = client.get("/sitemap.xml", base_url=B).get_data(as_text=True)
    return xml, [loc.split("teranga-ai.fr", 1)[-1] or "/" for loc in re.findall(r"<loc>([^<]+)</loc>", xml)]


def test_every_sitemap_page_has_a_google_friendly_title_and_description():
    client = _client()
    xml, paths = _sitemap_paths(client)
    assert re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", xml)
    problems = []
    for path in paths:
        page = client.get(path, base_url=B).get_data(as_text=True)
        title = html.unescape(re.search(r"<title>(.*?)</title>", page, re.S).group(1).strip())
        description = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', page).group(1))
        if not title or len(title) > 65:
            problems.append((path, "titre", len(title)))
        if not 70 <= len(description) <= 165:
            problems.append((path, "description", len(description)))
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
            json.loads(block)  # données structurées valides
    assert problems == []


def test_every_sitemap_page_has_canonical_and_share_tags():
    """Chaque page indexable a une URL canonique et un aperçu de partage (WhatsApp, Facebook, X)."""
    client = _client()
    _, paths = _sitemap_paths(client)
    problems = []
    for path in paths:
        page = client.get(path, base_url=B).get_data(as_text=True)
        canonical = re.search(r'<link rel="canonical" href="([^"]*)"', page)
        if not canonical or canonical.group(1).rstrip("/") != (B + path).rstrip("/"):
            problems.append((path, "canonical"))
        for tag in ("og:title", "og:description", "og:url", "og:image", "og:type"):
            if f'property="{tag}"' not in page:
                problems.append((path, tag))
        if 'name="twitter:card"' not in page:
            problems.append((path, "twitter:card"))
        if 'application/ld+json' not in page:
            problems.append((path, "json-ld"))
    assert problems == []


def test_place_page_has_faq_from_its_own_data():
    page = _client().get("/lieux/goree", base_url=B).get_data(as_text=True)
    assert "<h2>Questions fréquentes</h2>" in page and "Comment aller à Île de Gorée ?" in page
    assert '"FAQPage"' in page


def test_region_page_describes_the_region():
    page = _client().get("/regions/saint-louis", base_url=B).get_data(as_text=True)
    assert "La région en bref" in page and "Départements" in page and "thiéré" in page


def test_topic_pages_reuse_the_knowledge_base():
    client = _client()
    goree = client.get("/visiter-goree", base_url=B).get_data(as_text=True)
    assert "Histoire de l'île de Gorée" in goree and 'href="/lieux/goree"' in goree
    food = client.get("/specialites-senegal", base_url=B).get_data(as_text=True)
    assert "Plats et boissons à goûter" in food and "Yassa" in food


def test_long_place_names_get_a_shorter_title():
    from services.places import place_title

    assert place_title("Gorée", "Dakar") == "Gorée (Dakar) : histoire, que voir, carte | Teranga AI"
    long = place_title("Manufactures sénégalaises des arts décoratifs", "Thiès")
    assert len(long) <= 65 and long.startswith("Manufactures")


def test_emergency_page_lists_verified_numbers_and_works_offline():
    client = _client()
    page = client.get("/urgences", base_url=B).get_data(as_text=True)
    for number in ('href="tel:17"', 'href="tel:18"', 'href="tel:1515"', 'href="tel:+221800002020"'):
        assert number in page
    assert "/urgences" in client.get("/sitemap.xml", base_url=B).get_data(as_text=True)
    assert "'/urgences'" in client.get("/sw.js", base_url=B).get_data(as_text=True)
