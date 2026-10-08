"""Script d'audit SEO (scripts/audit_seo.py) : il doit repérer un défaut et valider le site tel quel."""

import os
import runpy

os.environ.setdefault("OPENAI_API_KEY", "test-key")

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "audit_seo.py")

GOOD = (
    '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    "<title>Guide du Sénégal | Teranga AI</title>"
    '<meta name="description" content="Un guide pratique du Sénégal avec des repères vérifiés, des lieux, des fêtes et des conseils de voyage.">'
    '<link rel="canonical" href="https://teranga-ai.fr/senegal">'
    + "".join(f'<meta property="{t}" content="x">' for t in ("og:title", "og:description", "og:url", "og:image", "og:type"))
    + '<meta name="twitter:card" content="summary_large_image">'
    '<script type="application/ld+json">{"@type": "WebPage"}</script></head><body><h1>Sénégal</h1></body></html>'
)


def test_a_complete_page_has_no_problem():
    module = runpy.run_path(SCRIPT, run_name="audit_seo")
    assert module["check_page"]("/senegal", GOOD) == []


def test_missing_tags_are_reported_in_french():
    module = runpy.run_path(SCRIPT, run_name="audit_seo")
    broken = (
        GOOD.replace('<link rel="canonical" href="https://teranga-ai.fr/senegal">', "")
        .replace('<meta name="twitter:card" content="summary_large_image">', "")
        .replace("<h1>Sénégal</h1>", "<h1>A</h1><h1>B</h1><img src='/x.png'>")
    )
    problems = module["check_page"]("/senegal", broken)
    assert "URL canonique manquante" in problems
    assert "twitter:card manquant" in problems
    assert "2 balise(s) h1 (attendu : 1)" in problems
    assert "1 image(s) sans alt" in problems


def test_noindex_and_apostrophes_in_description_are_handled():
    module = runpy.run_path(SCRIPT, run_name="audit_seo")
    page = GOOD.replace("Un guide pratique", "L'essentiel, un guide pratique").replace(
        "<title>", '<meta name="robots" content="noindex,follow"><title>'
    )
    problems = module["check_page"]("/senegal", page)
    assert problems == ["noindex sur une page du sitemap"]


def test_the_whole_site_passes_the_audit():
    module = runpy.run_path(SCRIPT, run_name="audit_seo")
    count, problems = module["audit"]()
    assert count > 150
    assert problems == []
