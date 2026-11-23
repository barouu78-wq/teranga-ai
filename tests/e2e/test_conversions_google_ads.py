"""Conversions Google Ads dans le navigateur (constat du 23 novembre 2026) : envoyées seulement après « Accepter »,
une fois par session et par action. gtag.js de Google est remplacé par un script vide : aucun accès réseau."""

import pytest

from services.google_ads_tag import google_ads_config

TAG = "AW-18578242897"
QUESTION = TAG + "/question_lbl1"
APPLI = TAG + "/appli_lbl22"
CONVERSIONS = """() => (window.dataLayer || []).map(a => Array.from(a))
  .filter(a => a[0] === 'event' && a[1] === 'conversion').map(a => a[2].send_to)"""


@pytest.fixture
def ads(monkeypatch):
    import app as app_module

    monkeypatch.setitem(app_module.app.config, "GOOGLE_ADS",
                        google_ads_config(TAG, f"question:{QUESTION},appli:{APPLI}"))


def _prepare(page, choice):
    page.route("https://www.googletagmanager.com/**", lambda route: route.fulfill(content_type="text/javascript",
                                                                                body="/* gtag simulé */"))
    page.route("**/chat", lambda route: route.fulfill(content_type="application/x-ndjson",
                                                      body='{"d":"Réponse simulée."}\n{"done":true}\n'))
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(page.base + "/")
    page.locator(f".teranga-ads-consent-panel [data-choice='{choice}']").click()


def _ask(page, text):
    page.fill("#heroInput", text)
    page.press("#heroInput", "Enter")
    page.get_by_text("Réponse simulée.").last.wait_for(timeout=5000)


def test_une_question_compte_une_seule_conversion_apres_accord(page, base_url, ads):
    page.base = base_url
    _prepare(page, "accept")
    _ask(page, "Comment aller à Gorée ?")
    assert page.evaluate(CONVERSIONS) == [QUESTION]
    page.fill("#input", "Et le prix ?")
    page.click("#send")
    page.get_by_text("Réponse simulée.").nth(1).wait_for(timeout=5000)
    assert page.evaluate(CONVERSIONS) == [QUESTION]  # une seule par session
    assert page.errors == []


def test_aucune_conversion_si_le_visiteur_refuse(page, base_url, ads):
    page.base = base_url
    requests = []
    page.on("request", lambda req: requests.append(req.url))
    _prepare(page, "reject")
    _ask(page, "Comment aller à Gorée ?")
    assert page.evaluate(CONVERSIONS) == []
    assert not any("googletagmanager" in url or "doubleclick" in url for url in requests)
    assert page.errors == []


def test_le_lien_de_l_appli_compte_une_conversion(page, base_url, ads, monkeypatch):
    monkeypatch.setenv("ANDROID_PLAY_PUBLIC", "1")  # le lien Google Play n'apparaît qu'une fois l'appli publique
    page.base = base_url
    page.route("https://www.googletagmanager.com/**", lambda route: route.fulfill(content_type="text/javascript",
                                                                                body="/* gtag simulé */"))
    page.goto(base_url + "/telecharger")
    page.locator(".teranga-ads-consent-panel [data-choice='accept']").click()
    page.evaluate("""() => document.querySelectorAll('a').forEach(a => a.addEventListener('click', e => e.preventDefault()))""")
    page.locator("a[href$='.apk']").first.click()
    page.locator("a[href*='play.google.com/store/apps']").first.click()
    assert page.evaluate(CONVERSIONS) == [APPLI]  # une seule, même après deux liens
    assert page.errors == []
