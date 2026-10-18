"""Photos d'un article Wikipédia : la photo principale choisie par ses rédacteurs passe en premier.

Le 17 octobre 2026, la carte « Ziguinchor » de l'accueil montrait « Aéroport de Ziguinchor.jpg » et une autre carte
« Aire de repos en face de l'AMP.jpg » : l'API renvoie les fichiers d'un article par ordre alphabétique, donc un nom en
« A » passait toujours devant. La photo principale de l'article (pageimages) donne le choix des rédacteurs.
"""

import io
import json

from services.images import _ARTICLE_CACHE, fetch_article_images


def _page(title):
    return {"title": title, "imageinfo": [{
        "mime": "image/jpeg", "width": 2000, "height": 1300, "extmetadata": {},
        "url": "https://upload.wikimedia.org/o/" + title.split(":", 1)[1].replace(" ", "_"),
        "thumburl": "https://upload.wikimedia.org/t/" + title.split(":", 1)[1].replace(" ", "_")}]}


IMAGES = {"query": {"pages": {str(i): _page(t) for i, t in enumerate(
    ["Fichier:Aéroport de Ziguinchor.jpg", "Fichier:Cathédrale de Ziguinchor.jpg", "Fichier:Ziguinchor - Port.jpg"])}}}


def _opener(lead, requested, fail_lead=False):
    def opener(req, timeout=5):
        requested.append(req.full_url)
        if "prop=pageimages" in req.full_url:
            if fail_lead:
                raise OSError("panne passagère")
            return io.BytesIO(json.dumps({"query": {"pages": {"1": {"title": "Ziguinchor", "pageimage": lead}}}}).encode())
        return io.BytesIO(json.dumps(IMAGES).encode())
    return opener


def _names(photos):
    return [p["page_url"].rsplit("/", 1)[-1] for p in photos]


def test_la_photo_principale_passe_avant_l_ordre_alphabetique():
    _ARTICLE_CACHE.clear()
    requested = []
    photos = fetch_article_images("Ziguinchor", urlopen_fn=_opener("Ziguinchor_-_Port.jpg", requested))
    assert _names(photos) == ["File:Ziguinchor_-_Port.jpg", "File:A%C3%A9roport_de_Ziguinchor.jpg",
                              "File:Cath%C3%A9drale_de_Ziguinchor.jpg"]


def test_sans_photo_principale_l_ordre_reste_le_meme():
    _ARTICLE_CACHE.clear()
    requested = []
    photos = fetch_article_images("Ziguinchor", urlopen_fn=_opener("", requested, fail_lead=True))
    assert _names(photos)[0] == "File:A%C3%A9roport_de_Ziguinchor.jpg"  # repli : ordre de l'API, sans erreur


def test_la_limite_garde_la_photo_principale():
    _ARTICLE_CACHE.clear()
    photos = fetch_article_images("Ziguinchor", limit=1, urlopen_fn=_opener("Ziguinchor_-_Port.jpg", []))
    assert _names(photos) == ["File:Ziguinchor_-_Port.jpg"]


def test_une_seule_photo_ne_demande_pas_la_photo_principale():
    _ARTICLE_CACHE.clear()
    requested = []
    seule = {"query": {"pages": {"1": _page("Fichier:Touba.jpg")}}}

    def opener(req, timeout=5):
        requested.append(req.full_url)
        return io.BytesIO(json.dumps(seule).encode())

    assert len(fetch_article_images("Touba", urlopen_fn=opener)) == 1
    assert not any("prop=pageimages" in url for url in requested)
