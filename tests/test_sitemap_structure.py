"""Le sitemap est lu par les moteurs de recherche : sa structure XML doit être irréprochable.

Ces tests analysent le XML réellement servi (et non des fragments de texte) : racine, espace de noms,
adresses, dates et cohérence avec robots.txt. Aucun accès réseau.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from urllib.parse import urlsplit

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest  # noqa: E402

from app import app  # noqa: E402

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
CHANGEFREQ = {"always", "hourly", "daily", "weekly", "monthly", "yearly", "never"}


@pytest.fixture(scope="module")
def client():
    return app.test_client()


@pytest.fixture(scope="module")
def sitemap(client):
    response = client.get("/sitemap.xml")
    return response, response.get_data(as_text=True)


@pytest.fixture(scope="module")
def robots(client):
    return client.get("/robots.txt").get_data(as_text=True)


@pytest.fixture(scope="module")
def entries(sitemap):
    root = ET.fromstring(sitemap[1])
    return list(root)


def _robots_sitemap_url(robots):
    lines = [line for line in robots.splitlines() if line.lower().startswith("sitemap:")]
    assert len(lines) == 1, "robots.txt doit annoncer exactement un sitemap"
    return lines[0].split(":", 1)[1].strip()


def test_served_as_xml_with_a_single_urlset_root(sitemap):
    response, body = sitemap
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/xml")
    assert body.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert body.rstrip().endswith("</urlset>")
    root = ET.fromstring(body)  # lève ParseError si le contenu est mal formé ou concaténé
    assert root.tag == NS + "urlset"
    assert body.count("<urlset") == 1 and body.count("</urlset>") == 1


def test_every_entry_is_a_url_with_one_loc(entries):
    assert 1 <= len(entries) <= 50000  # limite du protocole sitemaps
    for entry in entries:
        assert entry.tag == NS + "url"
        assert len(entry.findall(NS + "loc")) == 1
        assert (entry.findtext(NS + "loc") or "").strip()


def test_addresses_are_canonical_https_on_one_host_without_duplicates(entries, robots):
    locs = [entry.findtext(NS + "loc") for entry in entries]
    assert len(locs) == len(set(locs)), "adresses en double"
    announced = urlsplit(_robots_sitemap_url(robots))
    assert announced.scheme == "https" and announced.path == "/sitemap.xml"
    for loc in locs:
        assert loc == loc.strip() and not re.search(r"\s", loc), loc
        assert len(loc) <= 2048, loc
        parts = urlsplit(loc)
        assert parts.scheme == "https", loc
        assert parts.netloc == announced.netloc, loc  # même hôte que robots.txt
        assert not parts.query and not parts.fragment, loc
    assert any(urlsplit(loc).path == "/" for loc in locs), "l'accueil doit figurer au sitemap"


def test_dates_priorities_and_frequencies_are_valid(entries):
    for entry in entries:
        lastmod = entry.findtext(NS + "lastmod")
        assert lastmod, "lastmod manquant pour " + entry.findtext(NS + "loc")
        # W3C Datetime : AAAA-MM-JJ, ou date et heure ISO 8601.
        if "T" in lastmod:
            datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
        else:
            date.fromisoformat(lastmod)
        assert len(entry.findall(NS + "lastmod")) == 1
        priority = entry.findtext(NS + "priority")
        assert priority is not None and 0.0 <= float(priority) <= 1.0
        assert entry.findtext(NS + "changefreq") in CHANGEFREQ


def test_no_sitemap_page_is_blocked_by_robots(entries, robots):
    disallowed = [line.split(":", 1)[1].strip() for line in robots.splitlines() if line.lower().startswith("disallow:")]
    disallowed = [rule for rule in disallowed if rule]
    for entry in entries:
        path = urlsplit(entry.findtext(NS + "loc")).path
        for rule in disallowed:
            assert not path.startswith(rule), f"{path} est au sitemap mais interdit par « Disallow: {rule} »"


def test_robots_txt_is_plain_text_and_points_to_the_sitemap(client, robots):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    assert robots.startswith("User-agent: *")
    assert _robots_sitemap_url(robots).endswith("/sitemap.xml")
