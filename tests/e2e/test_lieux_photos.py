"""Photos d'une fiche de lieu (/lieux/<id>) quand le relais d'images refuse.

Vu le 15 novembre 2026 sur /lieux/rufisque : après la page Explorer (une trentaine de photos en quelques secondes), le
relais /image-proxy a répondu 429 (limite de 24 images par minute) et la fiche affichait une image cassée avec son
texte de remplacement. Comme la page Explorer et l'accueil, la fiche charge alors la photo directement chez
Wikimedia (autorisé par la CSP) ; si ça échoue aussi, la photo disparaît au lieu de rester cassée.
"""

import base64
import json

# Image PNG de 1 × 1 pixel.
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
IMAGES = {"images": [
    {"url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Rufisque.jpg",
     "display_url": "/image-proxy?url=https%3A%2F%2Fupload.wikimedia.org%2Fwikipedia%2Fcommons%2Fa%2Fab%2FRufisque.jpg",
     "alt": "Vieux Rufisque"},
    {"url": "https://upload.wikimedia.org/wikipedia/commons/c/cd/Rufisque2.jpg",
     "display_url": "/image-proxy?url=https%3A%2F%2Fupload.wikimedia.org%2Fwikipedia%2Fcommons%2Fc%2Fcd%2FRufisque2.jpg",
     "alt": "Rufisque"},
]}


def attendre(page, condition, delai=10):
    # wait_for_function évalue du texte dans la page, ce que la CSP du site interdit : on interroge depuis Python.
    for _ in range(delai * 10):
        if page.evaluate(condition):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"jamais vrai : {condition}")


def ouvrir(page, base_url, direct_ok):
    directes = []

    def wikimedia(route):
        directes.append(route.request.url)
        route.fulfill(body=PNG, content_type="image/png") if direct_ok else route.fulfill(status=404, body="")

    page.route(f"{base_url}/explorer-image**", lambda r: r.fulfill(body=json.dumps(IMAGES), content_type="application/json"))
    page.route(f"{base_url}/image-proxy**", lambda r: r.fulfill(
        status=429, headers={"Retry-After": "10"}, body="Trop de demandes d'images. Réessaie dans un instant.",
        content_type="text/plain"))
    page.route("https://upload.wikimedia.org/**", wikimedia)
    page.goto(base_url + "/lieux/rufisque")
    return directes


def test_relais_refuse_la_photo_vient_directement_de_wikimedia(page, base_url):
    ouvrir(page, base_url, direct_ok=True)
    hero = page.locator("#placeHero img")
    hero.wait_for()
    attendre(page, "[...document.querySelectorAll('#placeHero img, #gallery img')].every(i => i.complete && i.naturalWidth > 0)")
    assert hero.get_attribute("src").startswith("https://upload.wikimedia.org/")
    assert page.locator("#gallery img").count() == 2


def test_photo_introuvable_partout_disparait_au_lieu_de_rester_cassee(page, base_url):
    directes = ouvrir(page, base_url, direct_ok=False)
    attendre(page, "!document.querySelector('#placeHero img') && !document.querySelector('#gallery img')")
    assert len(directes) >= 2  # chaque photo a bien été tentée chez Wikimedia avant de disparaître
    assert page.locator("#placeHero").is_hidden()
