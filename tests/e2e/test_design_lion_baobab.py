"""Design « lion + baobab » vu dans un vrai navigateur, à la taille d'un téléphone (390 × 844).

Vérifie que la bannière s'affiche dans les deux thèmes, que le lion est bien dessiné (symbole SVG utilisé), que la
zone de question reste dans le premier écran, et que la bannière disparaît dès que la conversation commence.
Les réponses de `/chat` sont simulées : aucun appel réseau.
"""

import json

import pytest

PHONE = {"width": 390, "height": 844}


def open_home(page, base_url, theme):
    page.set_viewport_size(PHONE)
    page.add_init_script(
        "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}" % theme)
    page.goto(base_url + "/")
    page.locator(".hero-scene").wait_for(timeout=5000)


def box(page, selector):
    return page.locator(selector).first.bounding_box()


@pytest.mark.parametrize("theme,sky", [("light", "rgb(248, 217, 138)"), ("dark", "rgb(14, 26, 43)")])
def test_banner_lion_and_question_box_fit_the_first_phone_screen(page, base_url, theme, sky):
    open_home(page, base_url, theme)
    assert page.evaluate("document.body.dataset.theme") == theme
    assert sky in page.evaluate("getComputedStyle(document.querySelector('.scene-sky')).backgroundImage")
    for selector in (".scene-sky", ".scene-tree:not(.scene-far)", ".scene-lion svg", ".brand .mark svg"):
        dessin = box(page, selector)
        assert dessin and dessin["width"] > 20 and dessin["height"] > 20, selector
    question = box(page, "#heroInput")
    assert question["y"] + question["height"] <= PHONE["height"]  # visible sans faire défiler
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]  # pas de défilement horizontal
    assert page.evaluate("document.querySelector('.hero-scene').getAttribute('aria-hidden')") == "true"
    assert page.errors == []


def test_banner_hides_when_the_conversation_starts_and_the_answer_shows_the_lion(page, base_url):
    page.route(f"{base_url}/chat", lambda route: route.fulfill(
        body=json.dumps({"d": "Réponse de Teranga."}) + "\n", content_type="application/x-ndjson"))
    open_home(page, base_url, "light")
    page.fill("#heroInput", "Bonjour")
    page.click("#heroSend")
    page.get_by_text("Réponse de Teranga.").wait_for(timeout=5000)
    assert not page.is_visible(".hero-scene")
    avatar = box(page, ".assistant .avatar svg")
    assert avatar and avatar["width"] >= 24  # le lion dans la bulle de l'assistant
    assert page.errors == []
