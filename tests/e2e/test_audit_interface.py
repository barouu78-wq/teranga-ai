"""Audit de l'interface avec les règles d'interface de Vercel (vercel-labs/web-interface-guidelines, 5 octobre 2026).

Défauts trouvés le 13 octobre 2026, vérifiés ici dans un vrai navigateur :
- aucun lien « Aller au contenu » : au clavier, il fallait traverser tout l'en-tête ;
- l'accueil n'avait pas de zone principale (`<main>`) pour les lecteurs d'écran ;
- la zone de question ne montrait qu'un changement de couleur de bordure quand on y écrit ;
- la couleur de la barre du navigateur (theme-color) partait sur #0b0907 au lieu du fond de la page.
"""

import pytest

FONDS = {"light": "#fbf8f1", "dark": "#0b0d10"}


def set_theme(page, theme):
    page.add_init_script(
        "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}" % theme)


def test_home_skip_link_is_the_first_stop_and_jumps_to_main(page, base_url):
    page.goto(base_url + "/")
    page.keyboard.press("Tab")
    first = page.evaluate("({id: document.activeElement.id, text: document.activeElement.textContent.trim()})")
    assert first == {"id": "skipLink", "text": "Aller au contenu"}
    box = page.locator("#skipLink").bounding_box()
    assert box and box["y"] >= 0 and box["height"] >= 44  # visible à l'écran une fois atteint, zone tactile
    page.keyboard.press("Enter")
    assert page.evaluate("[document.activeElement.tagName, document.activeElement.id]") == ["MAIN", "stage"]
    assert page.errors == []


def test_home_skip_link_follows_the_language(page, base_url):
    page.goto(base_url + "/")
    page.click("#langs button[data-lang='en']")
    assert page.text_content("#skipLink").strip() == "Skip to content"
    assert page.errors == []


def test_secondary_page_skip_link_jumps_past_the_header(page, base_url):
    page.goto(base_url + "/lieux")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip-link"
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "contenu"
    # Le contenu principal suit immédiatement la cible.
    assert page.evaluate("document.getElementById('contenu').nextElementSibling.tagName") == "MAIN"
    assert page.errors == []


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_theme_color_matches_the_background_from_the_first_paint(page, base_url, theme):
    """Même sans home.js (réseau lent), la barre du navigateur a déjà la couleur du fond."""
    page.route(f"{base_url}/static/home.js*", lambda route: route.abort())
    set_theme(page, theme)
    page.goto(base_url + "/")
    assert page.get_attribute("#themeColor", "content") == FONDS[theme]


@pytest.mark.parametrize("width,field,box", [(390, "#heroInput", ".hero-ask"), (1280, "#input", ".composer")])
def test_question_box_shows_a_clear_focus_ring(page, base_url, width, field, box):
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(base_url + "/")
    page.focus(field)
    style = page.evaluate(
        "s => { const c = getComputedStyle(document.querySelector(s)); return [c.outlineStyle, parseFloat(c.outlineWidth)]; }",
        box)
    assert style[0] == "solid" and style[1] >= 2, style
    assert page.errors == []
