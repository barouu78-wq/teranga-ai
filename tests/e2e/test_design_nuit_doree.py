"""Design de la version 3.0 (« Nuit dorée », logo « Baobab doré ») vu dans un vrai navigateur, aux tailles de téléphone.

Vérifie :
- la bannière s'affiche dans les deux thèmes ;
- le logo et le baobab sont bien dessinés (le symbole SVG est résolu) ;
- la zone de question reste dans le premier écran, au-dessus de la barre d'onglets, du petit Android (360 × 560)
  au grand iPhone, avec et sans fête ;
- il n'y a pas de défilement horizontal ;
- la bannière disparaît dès que la conversation commence.

Les réponses de `/chat` sont simulées : aucun appel réseau.
"""

import json

import pytest

# Zones visibles réelles : grand iPhone, iPhone avec les barres de Safari, Android courant, iPhone SE, petit Android.
SCREENS = [(390, 844), (390, 664), (360, 640), (375, 548), (360, 560)]
MEASURE = """() => {
  const stage = document.getElementById('stage'), scene = document.querySelector('.hero-scene');
  return {stage: stage.getBoundingClientRect().bottom, input: document.getElementById('heroInput').getBoundingClientRect().bottom,
          scrollWidth: stage.scrollWidth, clientWidth: stage.clientWidth, scene: scene.getBoundingClientRect().height > 0};
}"""


def open_home(page, base_url, theme, size=(390, 844), query=""):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    page.add_init_script(
        "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}" % theme)
    page.goto(base_url + "/" + query)
    page.locator("#heroInput").wait_for(timeout=5000)


def drawn(page, selector):
    """Taille du dessin réellement rendu : la boîte du <use> est vide si le symbole #sn-… ne se résout pas."""
    return page.locator(selector).first.bounding_box()


@pytest.mark.parametrize("theme,sky", [("light", "rgb(247, 231, 191)"), ("dark", "rgb(7, 9, 12)")])
def test_banner_logo_and_baobab_are_drawn_in_both_themes(page, base_url, theme, sky):
    open_home(page, base_url, theme)
    assert page.evaluate("document.body.dataset.theme") == theme
    assert sky in page.evaluate("getComputedStyle(document.querySelector('.scene-sky')).backgroundImage")
    for selector in (".scene-tree:not(.scene-far) use", ".scene-logo use", ".brand .mark use"):
        box = drawn(page, selector)
        assert box and box["width"] > 20 and box["height"] > 20, selector
    assert page.evaluate("document.querySelector('.hero-scene').getAttribute('aria-hidden')") == "true"
    assert page.errors == []


@pytest.mark.parametrize("fete", ["", "korite"])
@pytest.mark.parametrize("size", SCREENS)
def test_question_box_stays_in_the_first_screen(page, base_url, size, fete):
    open_home(page, base_url, "light", size, f"?fete={fete}" if fete else "")
    m = page.evaluate(MEASURE)
    assert m["input"] <= m["stage"], m  # visible sans faire défiler, au-dessus de la barre d'onglets
    assert m["scrollWidth"] <= m["clientWidth"], m  # pas de défilement horizontal
    # Jour de fête sur un écran bas : la bande de la fête remplace la bannière.
    assert m["scene"] == (not fete or size[1] > 700), m
    assert page.errors == []


def test_banner_hides_when_the_conversation_starts_and_the_answer_shows_the_logo(page, base_url):
    page.route(f"{base_url}/chat", lambda route: route.fulfill(
        body=json.dumps({"d": "Réponse de Teranga."}) + "\n", content_type="application/x-ndjson"))
    open_home(page, base_url, "light")
    page.fill("#heroInput", "Bonjour")
    page.click("#heroSend")
    page.get_by_text("Réponse de Teranga.").wait_for(timeout=5000)
    assert not page.is_visible(".hero-scene")
    avatar = drawn(page, ".assistant .avatar use")
    assert avatar and avatar["width"] >= 20  # le logo dans la bulle de l'assistant
    assert page.errors == []
