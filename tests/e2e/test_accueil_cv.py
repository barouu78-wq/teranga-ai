"""Plan du 21 novembre 2026 : tout sur le CV pour l'emploi au Sénégal. Jusqu'ici, l'accueil (où arrivent la pub et
presque tous les visiteurs) n'avait aucun lien vers /cv. Une carte « Faire mon CV gratuit » s'affiche sous les thèmes
rapides, visible sur un téléphone sans faire défiler ; en anglais, elle dit que l'outil est en français."""

import datetime

PHONE = {"width": 390, "height": 844}


def _boite(page, selecteur):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect();"
                         " return {top: r.top, bottom: r.bottom, height: r.height}; }", selecteur)


def test_l_accueil_mene_au_cv_des_le_premier_ecran(page, base_url):
    page.set_viewport_size(PHONE)
    page.clock.install(time=datetime.datetime(2026, 10, 5, 11, 0))
    page.goto(base_url + "/")
    carte = page.locator("a#cvCta")
    carte.wait_for(timeout=5000)
    assert carte.get_attribute("href") == "/cv"
    assert "Faire mon CV gratuit" in carte.inner_text()
    boite, barre = _boite(page, "#cvCta"), _boite(page, "#tabbar")
    assert boite["height"] >= 44 and boite["bottom"] <= barre["top"], "visible sans faire défiler, au-dessus des onglets"
    assert _boite(page, "#heroChips")["bottom"] <= boite["top"]
    # Même ordre au clavier qu'à l'écran : la carte vient après les thèmes dans la page.
    assert page.evaluate("document.querySelector('#heroChips').compareDocumentPosition(document.querySelector('#cvCta'))"
                         " & Node.DOCUMENT_POSITION_FOLLOWING")
    page.click("#langs button[data-lang='en']")
    assert "CV" in carte.inner_text() and "French" in carte.inner_text()
    carte.click()
    page.wait_for_url("**/cv")
