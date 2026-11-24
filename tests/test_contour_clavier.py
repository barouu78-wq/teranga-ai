"""Contour clavier : visible dans tous les thèmes (contraste d'au moins 3 pour 1, WCAG 1.4.11).

Constat du 12 octobre 2026 (maquette de la version 9) : en thème jour, le contour or (`--nav-gold` #c97d12,
`--sen-gold` #d9a441) ne faisait que 2,97 et 2,04 pour 1 sur le fond crème. Il prend la couleur des liens
(`--link`), qui suit déjà les thèmes et les ambiances du site.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FICHIERS = {"templates/home.html": (ROOT / "templates" / "home.html").read_text(encoding="utf-8"),
            "static/site.css": (ROOT / "static" / "site.css").read_text(encoding="utf-8")}
CONTOUR = re.compile(r":focus-visible\{outline:\s*\d+px\s+solid\s+var\((--[\w-]+)\)")


def _luminance(hexa):
    rouge, vert, bleu = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (rouge, vert, bleu)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a, b):
    clair, sombre = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (clair + 0.05) / (sombre + 0.05)


@pytest.mark.parametrize("nom", FICHIERS)
def test_chaque_contour_clavier_prend_la_couleur_des_liens(nom):
    couleurs = CONTOUR.findall(FICHIERS[nom])
    assert couleurs, f"aucun contour clavier trouvé dans {nom}"
    assert set(couleurs) == {"--link"}, couleurs


def test_la_couleur_des_liens_contraste_avec_chaque_fond_de_chaque_theme():
    """Chaque bloc de jetons qui définit --link et un fond : contraste ≥ 3 pour 1 avec --bg, --surface, --surface-2."""
    blocs = 0
    for nom, texte in FICHIERS.items():
        for bloc in re.findall(r"\{[^{}]*\}", texte):
            jetons = dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", bloc))
            if "link" not in jetons or "bg" not in jetons:
                continue
            blocs += 1
            for fond in ("bg", "surface", "surface-2"):
                if fond in jetons:
                    assert contraste(jetons["link"], jetons[fond]) >= 3, (nom, jetons["link"], fond, jetons[fond])
    assert blocs >= 2  # au moins le thème jour et le thème nuit


def test_l_ancien_or_ne_suffisait_pas_en_theme_jour():
    """Garde la raison du changement : l'or sur le fond crème reste sous 3 pour 1."""
    assert contraste("#c97d12", "#fbf3e6") < 3
    assert contraste("#d9a441", "#fbf3e6") < 3
