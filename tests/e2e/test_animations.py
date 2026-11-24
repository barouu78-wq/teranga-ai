"""Animations du site (demande du propriétaire du 1er novembre 2026, après la maquette des animations : « je veux que
tu rajoutes des animations, faut rien retirer »).

Elles s'ajoutent à ce qui existe : arrivée en douceur des blocs de l'accueil, confettis qui tombent une fois sur la carte
JOJ et badge du jour qui apparaît, bulle de la question qui glisse depuis la droite, boutons qui s'enfoncent sous le
doigt, icône du thème qui tourne, fondu entre les pages. Rien n'est retiré : chaque bloc reste visible une fois
l'animation finie. Un visiteur qui a demandé moins d'animations (réglage du téléphone) n'en a aucune.
"""

import datetime
import json

ARRIVEES = ["#jojCard", ".hero-greet", "#heroTitle", "#heroText", ".audience-btn", ".hero-discover", ".plan-cta",
            ".fx-widget"]
ANIMATIONS = """(selecteurs) => selecteurs.map((s) => getComputedStyle(document.querySelector(s)).animationName)"""
FINIES = """() => document.getAnimations().filter((a) => a.effect && a.effect.getComputedTiming().iterations !== Infinity)
  .every((a) => a.playState === 'finished')"""


def open_home(page, base_url, reduce=False, size=(390, 844)):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    if reduce:
        page.emulate_media(reduced_motion="reduce")
    page.clock.install(time=datetime.datetime(2026, 11, 2, 11, 0))  # pendant les JOJ
    page.goto(base_url + "/")
    page.locator("#heroInput").wait_for(timeout=5000)


def test_home_blocks_arrive_with_an_animation_and_nothing_is_removed(page, base_url):
    open_home(page, base_url)
    noms = page.evaluate(ANIMATIONS, ARRIVEES)
    assert all(nom == "t-up" for nom in noms), dict(zip(ARRIVEES, noms))
    # La zone de question apparaît en fondu, sans bouger : elle reste dans le premier écran pendant l'animation.
    assert page.evaluate(ANIMATIONS, ["#heroAsk"]) == ["t-fade"]
    assert page.evaluate(ANIMATIONS, ["#jojDay"]) == ["t-pop"]
    assert page.evaluate("getComputedStyle(document.querySelector('.joj-confetti')).display") == "block"
    # Les confettis tombent derrière le texte et le bouton du guide, jamais par-dessus.
    dessus = page.evaluate("""() => {
      const z = (s) => Number(getComputedStyle(document.querySelector(s)).zIndex) || 0;
      return ['#jojDay', '.joj-title', '.joj-cta'].every((s) => z(s) > z('.joj-confetti'));
    }""")
    assert dessus
    page.wait_for_function(FINIES, timeout=5000)
    # #heroText et .journey-strip sont cachés sur téléphone par la mise en page (pas par l'animation). Depuis l'accueil
    # V5, la carte JOJ tient sur une ligne sur tous les téléphones : son texte « Le guide pratique » (#jojCta) est
    # caché par la mise en page, la flèche vers le guide (.joj-cta) reste.
    for selecteur in [s for s in ARRIVEES if s != "#heroText"] + ["#heroAsk", "#heroInput", ".joj-cta"]:
        assert page.is_visible(selecteur), selecteur
        assert page.evaluate("(s) => getComputedStyle(document.querySelector(s)).opacity", selecteur) == "1", selecteur
    assert page.evaluate("document.documentElement.scrollWidth") <= 390  # aucun défilement horizontal
    assert page.errors == []


def test_buttons_press_and_the_theme_icon_turns(page, base_url):
    open_home(page, base_url)
    for selecteur in (".audience-btn", "#heroSend", "#heroMic", ".tabbar a"):
        transition = page.evaluate("(s) => getComputedStyle(document.querySelector(s)).transitionProperty", selecteur)
        assert "scale" in transition, (selecteur, transition)
    assert "rotate" in page.evaluate("getComputedStyle(document.querySelector('#themeBtn svg')).transitionProperty")
    assert page.errors == []


def test_less_motion_turns_every_new_animation_off(page, base_url):
    open_home(page, base_url, reduce=True)
    noms = page.evaluate(ANIMATIONS, ARRIVEES + ["#heroAsk", "#jojDay"])
    assert all(nom == "none" for nom in noms), noms
    assert page.evaluate("getComputedStyle(document.querySelector('.joj-confetti')).display") == "none"
    assert "scale" not in page.evaluate("getComputedStyle(document.querySelector('.audience-btn')).transitionProperty")
    assert page.is_visible("#jojCard") and page.is_visible(".hero-discover")  # tout reste là, sans mouvement
    assert page.errors == []


def test_the_question_bubble_slides_in_from_the_right(page, base_url):
    page.route(f"{base_url}/chat", lambda route: route.fulfill(
        body=json.dumps({"d": "Réponse de Teranga."}) + "\n", content_type="application/x-ndjson"))
    open_home(page, base_url)
    page.fill("#heroInput", "Bonjour")
    page.click("#heroSend")
    page.get_by_text("Réponse de Teranga.").wait_for(timeout=5000)
    assert page.evaluate("getComputedStyle(document.querySelector('.msg.user.is-new')).animationName") == "t-right"
    assert page.errors == []


def test_secondary_pages_fade_in_too(page, base_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/joj-dakar-2026")
    assert page.evaluate("getComputedStyle(document.querySelector('main > article')).animationName") == "t-up"
    page.emulate_media(reduced_motion="reduce")
    assert page.evaluate("getComputedStyle(document.querySelector('main > article')).animationName") == "none"
    assert page.errors == []
