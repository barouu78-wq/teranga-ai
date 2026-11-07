"""V5, étape 2 « place pour lire » : sur téléphone, pendant le chat, la barre du bas ne garde que l'essentiel (Go V5 du
propriétaire, 7 novembre 2026).

Mesure avant le changement (390 × 664, une réponse affichée) : la barre du bas faisait 167 px de haut (rangée de
thèmes 44 px, saisie 59 px, ligne « Réponse en direct · Voix IA auto » 50 px) pour 369 px de lecture. Maintenant, la
rangée de thèmes et le texte « Réponse en direct » disparaissent sur téléphone (les suites proposées et « Plus de
détails » restent sous chaque réponse) ; le bouton « Voix IA auto » devient une icône à côté de la saisie, toujours
lisible par les lecteurs d'écran, car la lecture à voix haute est active par défaut et doit pouvoir se couper.
Sur ordinateur, rien ne change.
"""

import json

PHONE = {"width": 390, "height": 664}


def _repondre(page, base_url, texte="Réponse."):
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=json.dumps({"d": texte}) + "\n",
                                                       content_type="application/x-ndjson"))


def _boite(page, selecteur):
    return page.evaluate("(s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null;"
                         " const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, height: r.height, width: r.width}; }",
                         selecteur)


def _chat_sur_telephone(page, base_url, voix="0"):
    page.set_viewport_size(PHONE)
    if voix is not None:
        page.add_init_script(f"localStorage.setItem('teranga-voice', '{voix}')")
    _repondre(page, base_url)
    page.goto(base_url + "/")
    page.fill("#heroInput", "Bonjour")
    page.click("#heroSend")
    page.get_by_text("Réponse.").wait_for(timeout=5000)
    page.wait_for_timeout(300)


def test_sur_telephone_la_barre_du_bas_laisse_la_place_de_lire(page, base_url):
    _chat_sur_telephone(page, base_url)
    dock = _boite(page, ".dock")
    assert dock["height"] <= 75, dock  # 167 px avant
    assert _boite(page, "#stage")["height"] >= 450  # 369 px avant
    assert not page.locator("#chips").is_visible()
    assert not page.locator("#hint").is_visible()
    assert page.errors == []


def test_le_bouton_voix_reste_a_cote_de_la_saisie_et_accessible(page, base_url):
    _chat_sur_telephone(page, base_url, voix="0")
    bouton = page.locator("#voiceToggle")
    assert bouton.is_visible()
    voix, saisie = _boite(page, "#voiceToggle"), _boite(page, ".composer")
    assert voix["width"] >= 44 and voix["height"] >= 44, voix
    assert saisie["top"] - 1 <= voix["top"] and voix["bottom"] <= saisie["bottom"] + 1, (voix, saisie)  # même ligne
    # Le nom lu par un lecteur d'écran reste le texte du bouton ; l'état est donné par aria-pressed.
    assert page.get_by_role("button", name="Voix IA auto off").count() == 1
    assert bouton.get_attribute("aria-pressed") == "false"
    assert page.errors == []


def test_la_voix_active_par_defaut_se_coupe_d_un_appui(page, base_url):
    _chat_sur_telephone(page, base_url, voix=None)  # première visite : voix automatique active
    page.route(f"{base_url}/tts", lambda r: r.fulfill(status=204, body=""))
    bouton = page.locator("#voiceToggle")
    assert bouton.get_attribute("aria-pressed") == "true"
    assert "Voix IA auto on" in bouton.inner_text() or page.get_by_role("button", name="Voix IA auto on").count() == 1
    bouton.click()
    assert bouton.get_attribute("aria-pressed") == "false"
    assert page.get_by_role("button", name="Voix IA auto off").count() == 1
    assert page.evaluate("localStorage.getItem('teranga-voice')") == "0"


def test_sur_ordinateur_rien_ne_change(page, base_url):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.add_init_script("localStorage.setItem('teranga-voice', '0')")
    _repondre(page, base_url)
    page.goto(base_url + "/")
    page.fill("#input", "Bonjour")  # sur ordinateur, la saisie est en bas de l'écran dès l'accueil
    page.click("#send")
    page.get_by_text("Réponse.").wait_for(timeout=5000)
    page.wait_for_timeout(300)
    assert page.locator("#chips").is_visible()
    assert page.locator("#hint").is_visible()
    assert page.get_by_role("button", name="Voix IA auto off").is_visible()
    assert page.errors == []
