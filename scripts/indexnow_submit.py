#!/usr/bin/env python3
"""Signale à IndexNow (Bing, Yandex, Seznam…) toutes les pages du plan du site publié de Teranga AI.

    python scripts/indexnow_submit.py            # lit https://teranga-ai.fr/sitemap.xml et envoie
    python scripts/indexnow_submit.py --dry-run  # affiche les adresses sans rien envoyer

La clé n'est pas un secret : IndexNow la vérifie en lisant https://teranga-ai.fr/<clé>.txt (routes/system.py).
IndexNow demande de ne signaler que des pages nouvelles ou modifiées : à lancer après un changement de pages,
pas à chaque fusion. Python standard seulement.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

try:
    from scripts.seo_monitor import BASE_URL, USER_AGENT, fetch, parse_sitemap
except ImportError:  # lancé comme fichier : scripts/ est le dossier courant des imports
    from seo_monitor import BASE_URL, USER_AGENT, fetch, parse_sitemap

KEY = "8078ffb659c643b58bddddca48be0627"  # même valeur que INDEXNOW_KEY (app.py), vérifiée par un test
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10_000  # limite d'un envoi IndexNow


def build_payload(sitemap_xml: str) -> dict:
    pages, _children = parse_sitemap(sitemap_xml, BASE_URL)
    return {
        "host": "teranga-ai.fr",
        "key": KEY,
        "keyLocation": f"{BASE_URL}/{KEY}.txt",
        "urlList": pages[:MAX_URLS],
    }


def main(argv: list[str]) -> int:
    sitemap = fetch(f"{BASE_URL}/sitemap.xml")
    if sitemap["error"] or sitemap["status"] != 200:
        print(f"Plan du site illisible : {sitemap['status']} {sitemap['error'] or ''}", file=sys.stderr)
        return 1
    payload = build_payload(sitemap["body"])
    if not payload["urlList"]:
        print("Aucune page dans le plan du site : rien n'est envoyé.", file=sys.stderr)
        return 1
    if "--dry-run" in argv:
        print("\n".join(payload["urlList"]))
        print(f"{len(payload['urlList'])} pages (rien n'est envoyé)")
        return 0
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
            # Adresse fixe en https (ENDPOINT), jamais lue d'une entrée extérieure.
            print(f"IndexNow : {response.status}, {len(payload['urlList'])} pages signalées")
            return 0 if response.status in (200, 202) else 1
    except urllib.error.HTTPError as exc:
        print(f"IndexNow a refusé l'envoi : {exc.code} {exc.read(300).decode('utf-8', 'replace')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
