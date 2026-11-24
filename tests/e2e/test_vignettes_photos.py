"""Ticket images (audit du 22 novembre 2026) : les deux vignettes « à découvrir » de l'accueil.

Avant : la photo remplaçait le fond coloré sans être chargée d'abord. Si le proxy d'images échouait (404, 502, 503…),
la vignette devenait une case vide (la couleur disparaissait aussi) et la photo directe de Wikimedia n'était jamais
essayée, alors que les autres galeries du site le font déjà.
"""

import base64
import json

# PNG de 1 × 1 pixel.
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
DIRECT = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Lieu.jpg/500px-Lieu.jpg"


def _open(page, base_url, proxy_ok, direct_ok):
    page.set_viewport_size({"width": 390, "height": 844})
    image = {"url": DIRECT, "display_url": "/image-proxy?url=" + DIRECT, "alt": "Lieu"}
    page.route("**/explorer-image*", lambda route: route.fulfill(content_type="application/json",
                                                                 body=json.dumps({"images": [image]})))
    # Fonction et non motif : « * » ne traverse pas les « / » de l'adresse passée en paramètre.
    page.route(lambda url: "/image-proxy?" in url, lambda route: route.fulfill(status=200, content_type="image/png", body=PNG)
               if proxy_ok else route.fulfill(status=502, content_type="text/plain", body="Image indisponible"))
    page.route(DIRECT, lambda route: route.fulfill(status=200, content_type="image/png", body=PNG)
               if direct_ok else route.fulfill(status=404, body=""))
    page.goto(base_url + "/")
    page.locator(".place-tile-img").first.wait_for(timeout=5000)


def _wait_backgrounds(page, ok, timeout=5.0):
    """Attend que chaque vignette ait le bon fond. Pas de wait_for_function : la CSP du site interdit l'évaluation
    de texte JavaScript ; page.evaluate d'une fonction reste permis."""
    import time

    end = time.monotonic() + timeout
    while True:
        images = [tile["image"] for tile in _tiles(page)]
        if images and all(ok(image) for image in images):
            return images
        assert time.monotonic() < end, images
        page.wait_for_timeout(100)


def _tiles(page):
    return page.evaluate("""() => [...document.querySelectorAll('.place-tile-img')].map(b => {
      const s = getComputedStyle(b);
      return {image: s.backgroundImage, color: s.backgroundColor, height: b.getBoundingClientRect().height};
    })""")


def test_la_photo_passe_par_le_proxy(page, base_url):
    _open(page, base_url, proxy_ok=True, direct_ok=False)
    _wait_backgrounds(page, lambda image: "image-proxy" in image)
    assert page.errors == []


def test_proxy_en_echec_la_photo_directe_prend_le_relais(page, base_url):
    _open(page, base_url, proxy_ok=False, direct_ok=True)
    _wait_backgrounds(page, lambda image: image.startswith('url("https://upload.wikimedia.org/')
                      and "image-proxy" not in image)
    assert page.errors == []


def test_sans_aucune_photo_la_vignette_garde_sa_couleur(page, base_url):
    _open(page, base_url, proxy_ok=False, direct_ok=False)
    page.wait_for_timeout(1500)  # le temps des deux essais
    for tile in _tiles(page):
        assert tile["image"] == "none", tile  # aucune image cassée en fond
        assert tile["color"] not in ("rgba(0, 0, 0, 0)", "transparent"), tile  # la couleur reste
        assert tile["height"] >= 90, tile
    assert page.errors == []
