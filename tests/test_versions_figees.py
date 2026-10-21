"""Bibliothèques de production à versions figées.

Render réinstalle tout à chaque mise en ligne (sans cache) : avec des fourchettes de versions, une nouvelle
version d'une bibliothèque arriverait en ligne sans avoir été testée (anthropic 1.15.0 le 20 octobre 2026,
1.17.0 le lendemain, sans changement de notre côté). Les mises à jour passent par Dependabot, tests d'abord.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGEE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*==[0-9][^\s;]*$")


def _lignes():
    for ligne in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if ligne:
            yield ligne


def test_chaque_bibliotheque_de_production_a_une_version_figee():
    lignes = list(_lignes())
    assert lignes
    assert [ligne for ligne in lignes if not FIGEE.match(ligne)] == []


def test_les_bibliotheques_utilisees_par_le_code_sont_listees():
    noms = {ligne.split("==", 1)[0].lower() for ligne in _lignes()}
    for nom in ("flask", "werkzeug", "gunicorn", "openai", "anthropic", "redis", "httpx", "pillow", "python-dotenv"):
        assert nom in noms
