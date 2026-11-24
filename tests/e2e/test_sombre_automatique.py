"""Le « thème sombre pour les sites » de Chrome ne doit jamais repeindre Teranga AI.

Constat du 12 octobre 2026 (photo de l'application Android, 23 h 35) : Chrome assombrissait lui-même la page
par-dessus notre thème de nuit. Le baobab devenait gris clair sur une lune sombre, le titre presque invisible, les
boutons or viraient à l'orange et la bande du drapeau perdait son jaune.

Cause : la racine déclarait `color-scheme: light`, ce qui autorise cet assombrissement automatique. La racine
déclare maintenant `only light` le jour (assombrissement interdit) et `dark` avec notre thème de nuit.

L'assombrissement est simulé avec l'outil de développement de Chromium (Emulation.setAutoDarkModeOverride), système
en mode sombre comme sur le téléphone ; on lit un vrai pixel du fond dans une capture.
"""

import io

import pytest
from PIL import Image

# Fonds attendus, en RVB (jetons --bg de templates/home.html et static/site.css).
FOND_JOUR = (0xFB, 0xF8, 0xF1)  # « Nuit dorée » le jour : #fbf8f1


def open_page(page, base_url, path, theme, auto_dark):
    page.set_viewport_size({"width": 390, "height": 844})
    if auto_dark:
        # Comme sur le téléphone : Chrome n'assombrit les sites que lorsque le système est en mode sombre.
        page.emulate_media(color_scheme="dark")
        page.context.new_cdp_session(page).send("Emulation.setAutoDarkModeOverride", {"enabled": True})
    page.add_init_script(
        "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}" % theme)
    page.goto(base_url + path)
    page.wait_for_load_state("load")


def background_pixel(page):
    """Couleur réellement peinte dans la marge gauche (fond de la page), à mi-hauteur."""
    png = page.screenshot(clip={"x": 4, "y": 300, "width": 1, "height": 1})
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((0, 0))


def close(a, b, tolerance=6):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


@pytest.mark.parametrize("path", ["/", "/lieux"])
def test_chrome_auto_dark_does_not_repaint_the_light_theme(page, base_url, path):
    open_page(page, base_url, path, "light", auto_dark=True)
    pixel = background_pixel(page)
    assert close(pixel, FOND_JOUR), f"{path} : fond peint en {pixel}, attendu {FOND_JOUR} (assombri par Chrome)"
    assert page.errors == []


@pytest.mark.parametrize("theme,expected", [("light", "light only"), ("dark", "dark")])
def test_home_root_declares_its_real_color_scheme(page, base_url, theme, expected):
    """Avec notre thème de nuit, la racine annonce « dark » : Chrome sait que la page est déjà sombre."""
    open_page(page, base_url, "/", theme, auto_dark=False)
    assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == expected
    assert page.errors == []


@pytest.mark.parametrize("theme,expected", [("light", "light only"), ("dark", "dark")])
def test_secondary_pages_root_declares_its_real_color_scheme(page, base_url, theme, expected):
    open_page(page, base_url, "/lieux", theme, auto_dark=False)
    assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == expected
    assert page.errors == []
