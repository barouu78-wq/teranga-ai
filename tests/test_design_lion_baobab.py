"""Design « lion + baobab », couleurs « Vert Sénégal » (jour) et « Nuit verte » (choix du propriétaire, 12 octobre 2026).

Le lion et le baobab sont les deux symboles des armoiries du Sénégal. Les dessins sont originaux, en SVG dans la
page (aucune image ni police venant d'un autre domaine). Le lion est dessiné une seule fois par page : symbole
#sn-lion dans l'accueil, LION_SVG dans l'en-tête des pages secondaires ; ce test garde les deux identiques.
"""
import re
from pathlib import Path

import pytest

from services.site_layout import LION_SVG

ROOT = Path(__file__).resolve().parent.parent
HOME = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
SITE_CSS = (ROOT / "static" / "site.css").read_text(encoding="utf-8")


def symbole(nom):
    trouve = re.search(rf'<symbol id="{nom}" viewBox="[^"]+">(.*?)</symbol>', HOME, re.S)
    assert trouve, f"symbole {nom} absent de l'accueil"
    return trouve.group(1)


def _luminance(hexa):
    rouge, vert, bleu = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (rouge, vert, bleu)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a, b):
    clair, sombre = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (clair + 0.05) / (sombre + 0.05)


def blocs_de_couleurs(texte):
    """Blocs de jetons qui définissent une palette complète (fond, texte, accent)."""
    for bloc in re.findall(r"\{[^{}]*\}", texte):
        jetons = dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", bloc))
        if {"bg", "ink", "muted", "accent", "accent-ink"} <= set(jetons):
            yield jetons


def test_le_lion_est_le_meme_sur_l_accueil_et_les_autres_pages():
    assert symbole("sn-lion") == LION_SVG


def test_le_logo_et_l_avatar_de_l_accueil_utilisent_le_lion():
    entete = HOME.split('<div class="brand">', 1)[1].split("</div>", 1)[0]
    assert '<use href="#sn-lion"/>' in entete
    avatar = re.search(r"const AVATAR_SVG='([^']*)'", HOME_JS).group(1)
    assert '<use href="#sn-lion"/>' in avatar


def test_la_banniere_est_decorative_avec_baobab_drapeau_et_lion():
    banniere = '<div class="hero-scene"' + HOME.split('<div class="hero-scene"', 1)[1].split('<div class="hero-signature"', 1)[0]
    assert 'aria-hidden="true"' in banniere.split(">", 1)[0]
    assert '<use href="#sn-baobab"/>' in banniere and '<use href="#sn-lion"/>' in banniere
    assert banniere.count("<i></i>") == 3  # bande vert, or, rouge
    for rang, couleur in enumerate(("#0f6a43", "#f0c63d", "#c93636"), 1):
        assert f".scene-flag i:nth-child({rang}){{background:{couleur}}}" in HOME


@pytest.mark.parametrize("dessin", ["sn-lion", "sn-baobab", "LION_SVG"])
def test_les_dessins_ne_chargent_rien_de_l_exterieur(dessin):
    texte = LION_SVG if dessin == "LION_SVG" else symbole(dessin)
    for interdit in ("http", "<script", "<image", "href=", "url(", "<foreignObject", "on"):
        if interdit == "on":
            assert not re.search(r"\son\w+=", texte), "attribut d'événement dans un dessin"
        else:
            assert interdit not in texte, interdit


def test_les_pages_secondaires_ont_le_lion_dans_l_en_tete():
    from app import app

    page = app.test_client().get("/a-propos", environ_base={"REMOTE_ADDR": "203.0.113.71"})
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    entete = html.split('<span class="site-mark">', 1)[1].split("</span>", 1)[0]
    assert LION_SVG in entete and 'aria-hidden="true"' in entete


@pytest.mark.parametrize("nom,texte", [("templates/home.html", HOME), ("static/site.css", SITE_CSS)])
def test_chaque_palette_reste_lisible(nom, texte):
    """WCAG : texte ≥ 4,5 pour 1 (corps, discret, liens, titres, texte des boutons) ; bouton contre le fond ≥ 3 pour 1."""
    palettes = list(blocs_de_couleurs(texte))
    assert len(palettes) >= 2, nom  # au moins le jour et la nuit
    for jetons in palettes:
        for fond in ("bg", "surface", "surface-2"):
            if fond in jetons:
                assert contraste(jetons["ink"], jetons[fond]) >= 4.5, (nom, "ink", fond)
                assert contraste(jetons["muted"], jetons[fond]) >= 4.5, (nom, "muted", fond)
                for texte_couleur in ("link", "title"):
                    if texte_couleur in jetons:
                        assert contraste(jetons[texte_couleur], jetons[fond]) >= 4.5, (nom, texte_couleur, fond)
        assert contraste(jetons["accent-ink"], jetons["accent"]) >= 4.5, (nom, "accent-ink")
        assert contraste(jetons["accent"], jetons["bg"]) >= 3, (nom, "accent")


@pytest.mark.parametrize("nom,texte", [("templates/home.html", HOME), ("static/site.css", SITE_CSS)])
def test_le_jour_est_vert_senegal_et_la_nuit_verte(nom, texte):
    palettes = list(blocs_de_couleurs(texte))
    jour = [p for p in palettes if p["bg"] == "#f7f3e8"]
    nuit = [p for p in palettes if p["bg"] == "#0e1512"]
    assert jour and all(p["accent"] == "#0f6a43" for p in jour), nom
    assert nuit and all(p["accent"] == "#e3a33b" for p in nuit), nom
    for ancienne in ("#111215", "#b5451b", "#fbf3e6", "#7a2c10", "122,44,16"):
        assert ancienne not in texte, f"ancienne palette encore présente : {ancienne}"
