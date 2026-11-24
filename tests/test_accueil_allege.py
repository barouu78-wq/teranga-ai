"""Accueil allégé (« Go » du propriétaire, 23 novembre 2026 : « ça fait beaucoup… on devrait encore réduire »).

Sur iPhone, l'accueil montrait 49 boutons et liens. Restent la question, les thèmes rapides, « Faire mon CV » et
WhatsApp. Partent : « Je suis… » (l'IA répond à tout le monde, la question suffit), « À découvrir » (déjà dans
l'onglet Lieux), le convertisseur (le chat convertit : « 100 euros en FCFA »), « Copier le lien » et la carte de
l'appli Android. Les liens des guides restent dans la page pour Google, repliés derrière « Guides du Sénégal ».
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from home_source import served_home  # noqa: E402

B = "https://teranga-ai.fr"


def _accueil():
    return served_home(app_module.app.test_client())


def test_les_blocs_retires_ne_sont_plus_dans_l_accueil():
    html = _accueil()
    for absent in ('class="audience-btn', 'id="audienceMode"', 'id="fxWidget"', 'id="copyLink"',
                   'class="hero-discover"', 'id="planCta"', "__DISCOVER_TILES__", 'class="place-tile"'):
        assert absent not in html, absent


def test_l_essentiel_reste():
    html = _accueil()
    for present in ('id="heroInput"', 'id="heroChips"', 'id="cvCta" href="/cv"', 'id="waShare"', 'id="tabbar"'):
        assert present in html, present


def test_les_guides_sont_replies_mais_toujours_lus_par_google():
    html = _accueil()
    bloc = re.search(r'<details class="guide-section"([^>]*)>(.*?)</details>', html, re.S)
    assert bloc, "guides non repliés"
    assert "open" not in bloc.group(1)  # fermé par défaut
    assert "<summary" in bloc.group(2) and "Guides du Sénégal" in bloc.group(2)
    liens = re.findall(r'<a href="(/[^"]*)"', bloc.group(2))
    for chemin in ("/dakar", "/demarches-senegal", "/emploi-senegal", "/en/senegal-travel-guide", "/telecharger"):
        assert chemin in liens, chemin


def test_l_accueil_part_toujours_du_profil_general_sans_appel_aux_taux():
    html = _accueil()
    assert "storageGet('teranga-audience'" not in html  # un ancien choix « Touriste » ne reste pas caché
    assert "const audience='general'" in html
    assert "fetch('/exchange-rates'" not in html


def test_l_ia_ne_renvoie_plus_vers_le_convertisseur_retire():
    """Dollar, livre : le taux change, l'IA renvoie vers les cours de référence de la BCEAO (la source du convertisseur)."""
    from services.calculators import calculation_block
    from services.quick_answers import quick_answer

    bloc = calculation_block("100 dollars en FCFA")
    assert "convertisseur" not in bloc.lower() and "cours de référence de la BCEAO (bceao.int)" in bloc
    reponse = (quick_answer({"message": "100 euros en FCFA", "language": "fr"}, {}) or {}).get("reply", "")
    assert "65 595,70 FCFA" in reponse
    assert "onvertisseur" not in reponse and "bceao.int" in reponse
