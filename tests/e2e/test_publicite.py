"""Pages avec annonce Google (services/adsense.py) : la CSP stricte ne doit rien casser de nos pages.

Relecture Gitar de #598 : sous cette CSP, l'attribut onsubmit de la recherche de /lieux était bloqué, et Entrée
rechargeait la page en perdant le filtre. Le script de Google est bloqué ici (rien ne sort de la machine) : seul
compte le comportement de nos propres scripts.
"""

import pytest

from services.adsense import adsense_config


@pytest.fixture
def annonces(monkeypatch):
    from app import app

    monkeypatch.setitem(app.config, "ADSENSE", adsense_config("ca-pub-1234567890123456", "9876543210"))


def test_entree_dans_la_recherche_des_lieux_ne_recharge_pas_la_page(annonces, page, base_url):
    erreurs = []
    page.on("console", lambda message: erreurs.append(message.text) if "Content Security Policy" in message.text else None)
    page.goto(base_url + "/lieux")
    assert page.locator("ins.adsbygoogle").count() == 1
    page.evaluate("window.__memePage = true")
    page.fill("#place-q", "goree")
    page.locator("#place-count").filter(has_text="lieu").wait_for()
    page.press("#place-q", "Enter")
    page.wait_for_load_state("load")
    assert page.evaluate("window.__memePage === true"), "Entrée a rechargé la page"
    assert page.input_value("#place-q") == "goree"
    assert page.url == base_url + "/lieux"
    # Nos scripts tournent sous la CSP stricte : seul le script de Google (bloqué par le test) peut manquer.
    assert not [e for e in erreurs if "googlesyndication" not in e], erreurs
