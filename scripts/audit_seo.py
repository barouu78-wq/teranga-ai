"""Audit SEO de toutes les pages du sitemap, sans réseau (client de test Flask).

    python scripts/audit_seo.py            # affiche les problèmes, code de sortie 1 s'il y en a
    python scripts/audit_seo.py --json     # même résultat, lisible par un script

Vérifie pour chaque page : titre (≤ 65 caractères), description (70 à 165), URL canonique égale à
l'adresse du sitemap, un seul <h1>, balises Open Graph et Twitter, données structurées, attribut
lang, viewport, images sans alt, absence de noindex ; puis les titres et descriptions en double.
Ne contacte pas le site en ligne : il audite le code tel qu'il sera déployé.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "https://teranga-ai.fr"
SHARE_TAGS = ("og:title", "og:description", "og:url", "og:image", "og:type")


def _first(pattern: str, page: str) -> str | None:
    match = re.search(pattern, page, re.S | re.I)
    return match.group(1).strip() if match else None


def _meta(page: str, key: str, attr: str = "name") -> str | None:
    """Contenu d'une balise <meta>, guillemets doubles ou simples, dans les deux ordres d'attributs."""
    for quote in ('"', "'"):
        q = re.escape(quote)
        for pattern in (
            rf"<meta[^>]+{attr}={q}{re.escape(key)}{q}[^>]+content={q}([^{quote}]*){q}",
            rf"<meta[^>]+content={q}([^{quote}]*){q}[^>]+{attr}={q}{re.escape(key)}{q}",
        ):
            value = _first(pattern, page)
            if value is not None:
                return html.unescape(value)
    return None


def check_page(path: str, page: str) -> list[str]:
    """Liste des problèmes d'une page (vide si tout est conforme)."""
    problems = []
    title = _first(r"<title[^>]*>(.*?)</title>", page)
    title = html.unescape(title) if title else ""
    description = _meta(page, "description") or ""
    canonical = _first(r'<link[^>]+rel="canonical"[^>]+href="([^"]*)"', page)
    if not title:
        problems.append("titre manquant")
    elif len(title) > 65:
        problems.append(f"titre trop long ({len(title)} caractères)")
    if not description:
        problems.append("description manquante")
    elif not 70 <= len(description) <= 165:
        problems.append(f"description de {len(description)} caractères (attendu : 70 à 165)")
    if not canonical:
        problems.append("URL canonique manquante")
    elif canonical.rstrip("/") != (BASE + path).rstrip("/"):
        problems.append(f"canonique différente de l'adresse : {canonical}")
    h1 = len(re.findall(r"<h1[\s>]", page, re.I))
    if h1 != 1:
        problems.append(f"{h1} balise(s) h1 (attendu : 1)")
    problems += [f"{tag} manquant" for tag in SHARE_TAGS if _meta(page, tag, "property") is None]
    if _meta(page, "twitter:card") is None:
        problems.append("twitter:card manquant")
    if not _first(r"<html[^>]+lang=[\"']([^\"']*)", page):
        problems.append("attribut lang manquant sur <html>")
    if "viewport" not in page:
        problems.append("viewport manquant")
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    if not blocks:
        problems.append("données structurées (JSON-LD) manquantes")
    for block in blocks:
        try:
            json.loads(block)
        except ValueError:
            problems.append("JSON-LD invalide")
    if "noindex" in (_meta(page, "robots") or ""):
        problems.append("noindex sur une page du sitemap")
    without_alt = len(re.findall(r"<img(?![^>]*\balt=)[^>]*>", page, re.I))
    if without_alt:
        problems.append(f"{without_alt} image(s) sans alt")
    return problems


def audit(client=None) -> tuple[int, list[tuple[str, str]]]:
    """(nombre de pages du sitemap, [(chemin, problème)...])."""
    if client is None:
        from app import app

        client = app.test_client()
    sitemap = client.get("/sitemap.xml", base_url=BASE).get_data(as_text=True)
    locations = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    problems: list[tuple[str, str]] = []
    titles: Counter = Counter()
    descriptions: Counter = Counter()
    for location in locations:
        path = location.split("teranga-ai.fr", 1)[-1] or "/"
        response = client.get(path, base_url=BASE)
        if response.status_code != 200:
            problems.append((path, f"réponse HTTP {response.status_code}"))
            continue
        page = response.get_data(as_text=True)
        problems += [(path, problem) for problem in check_page(path, page)]
        titles[html.unescape(_first(r"<title[^>]*>(.*?)</title>", page) or "")] += 1
        descriptions[_meta(page, "description") or ""] += 1
    problems += [("(plusieurs pages)", f"titre en double : {t}") for t, n in titles.items() if t and n > 1]
    problems += [("(plusieurs pages)", f"description en double : {d[:70]}") for d, n in descriptions.items() if d and n > 1]
    if len(locations) != len(set(locations)):
        problems.append(("/sitemap.xml", "adresse en double dans le sitemap"))
    return len(locations), problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true", help="résultat en JSON")
    args = parser.parse_args(argv)
    count, problems = audit()
    if args.json:
        print(json.dumps({"pages": count, "problemes": problems}, ensure_ascii=False, indent=1))
    else:
        print(f"{count} pages dans le sitemap, {len(problems)} problème(s)")
        for path, problem in problems:
            print(f"  {path} : {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
