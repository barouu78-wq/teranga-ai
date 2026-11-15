"""Relecture de l'accueil avec le skill revue-interface (13 novembre 2026, « Go » du propriétaire).

- Pas d'émoji comme icône d'interface (AGENTS.md) : boutons, liens et titres du projet et des parcours. Les vœux des
  jours de fête et le drapeau à côté de l'indicatif +221 sont du contenu, pas des icônes : ils restent.
- Un seul ton : le tutoiement, déjà majoritaire (chat, projet) ; les descriptions pour les moteurs de recherche
  (balises <meta>) ne sont pas l'écran et gardent « vos ».
- Typographie française : espace insécable avant « ? » et « : » dans les textes relevés, et dans « 50 000 ».
- L'avion du profil « Touriste » (U+2708) et la double flèche « Diaspora » (U+2194) restent en glyphe texte sur iPhone
  (sélecteur U+FE0E), sinon iOS les dessine en émoji couleur.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "home.js").read_text(encoding="utf-8")
EMOJI = re.compile("[\U0001F300-\U0001FAFF]")
BODY = HTML.split("<body", 1)[1]


def test_aucun_emoji_dans_les_boutons_liens_et_titres_de_l_accueil():
    for balise in re.findall(r"<(?:button|a|h1|h2|h3|summary)\b[^>]*>.*?</(?:button|a|h1|h2|h3|summary)>", BODY, re.S):
        if 'id="fxCard' in balise:
            continue
        assert not EMOJI.search(balise), balise[:120]


def test_aucun_emoji_dans_les_libelles_du_script_hors_voeux_de_fete():
    sans_voeux = re.sub(r"\n\s*(fr|en):\{independance:.*", "", JS)
    sans_voeux = "\n".join(ligne for ligne in sans_voeux.splitlines() if not ligne.lstrip().startswith("//"))
    trouves = sorted({m.group(0) for m in EMOJI.finditer(sans_voeux)})
    assert not trouves, trouves


def test_les_parcours_ont_de_vraies_icones():
    bande = re.search(r'<div class="journey-strip".*?</div>', BODY, re.S).group(0)
    assert bande.count("<svg") == 2 and not EMOJI.search(bande)


def test_un_seul_ton_le_tutoiement_sur_l_ecran():
    fr = re.search(r"\nconst T=\{\nfr:\{(.*?)\n\},\nen:\{", JS, re.S).group(1)
    assert not re.search(r"\b(vous|votre|vos)\b", BODY, re.I)
    assert not re.search(r"\b(vous|votre|vos)\b", fr, re.I)
    assert "'Toutes tes questions'" in JS


def test_espaces_insecables_dans_les_textes_releves():
    for texte in ("Une question sur le Sénégal ?", "Où veux-tu commencer ?", "carte d’identité ?",
                  "voyageurs : démarches", "Ex. 50 000", "Ex. 100 000"):
        assert texte in HTML, texte
    assert "heroTitle:'Une question sur le Sénégal ?'" in JS
    assert "'Fiche : '" in JS


def test_avion_et_double_fleche_en_glyphe_texte():
    assert "✈︎</span>" in HTML and "↔︎</span>" in HTML
