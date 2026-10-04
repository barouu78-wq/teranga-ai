"""Accès au code de l'accueil pour les tests.

Le script principal de l'accueil vit dans static/home.js (mis en cache par le
navigateur) ; les contrats qui portent sur ce code lisent gabarit + script.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def home_source() -> str:
    template = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    script = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
    return template + "\n" + script


def served_home(client) -> str:
    """Page d'accueil servie + script réellement servi via son URL versionnée."""
    html = client.get("/").get_data(as_text=True)
    match = re.search(r'<script src="(/static/home\.js\?v=[0-9a-f]+)"></script>', html)
    assert match, "script de l'accueil introuvable"
    response = client.get(match.group(1))
    assert response.status_code == 200
    return html + "\n" + response.get_data(as_text=True)
