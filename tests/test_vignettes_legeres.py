"""Photos de « À découvrir » : vignette Wikimedia de 500 px au lieu de 1 280 px.

Journaux de production du 17 octobre 2026 : chaque photo d'une carte de 170 px pesait de 185 à 537 Ko (vignette de
1 280 px), soit jusqu'à 900 Ko pour les deux cartes de l'accueil sur un téléphone. Les fiches des lieux gardent
leurs grandes photos.
"""

import os

from flask import Flask

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from home_source import home_source  # noqa: E402
from routes.explorer import register_explorer_routes  # noqa: E402
from services.images import image_proxy_url, smaller_thumb  # noqa: E402

GRANDE = ("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Lac_Retba_S%C3%A9n%C3%A9gal_01.jpg/"
          "1280px-Lac_Retba_S%C3%A9n%C3%A9gal_01.jpg")


def test_meme_photo_en_vignette_plus_etroite():
    petite = smaller_thumb(GRANDE, 500)
    assert petite == GRANDE.replace("/1280px-", "/500px-")


def test_jamais_agrandie_ni_inventee():
    deja_petite = GRANDE.replace("/1280px-", "/330px-")
    assert smaller_thumb(deja_petite, 500) == deja_petite  # pas d'agrandissement
    originale = "https://upload.wikimedia.org/wikipedia/commons/6/6b/Lac_Retba.jpg"
    assert smaller_thumb(originale, 500) == originale  # pas une vignette : intacte
    assert smaller_thumb(GRANDE, 512) == GRANDE  # hors des paliers que Wikimedia sert : intacte
    ailleurs = "https://example.com/wikipedia/commons/thumb/a/ab/x.jpg/1280px-x.jpg"
    assert smaller_thumb(ailleurs, 500) == ailleurs  # seulement les adresses Wikimedia du relais


def _client():
    app = Flask(__name__)
    register_explorer_routes(
        app, {"places": [], "regions": []}, lambda query, limit=4: [], lambda query, limit=4: [{"url": GRANDE}],
        image_proxy_url,
    )
    return app.test_client()


def test_les_cartes_demandent_500_px_et_les_fiches_gardent_1280():
    client = _client()
    carte = client.get("/explorer-image?query=Lac+Rose&w=500").get_json()["images"][0]
    assert "/500px-" in carte["url"] and carte["display_url"] == image_proxy_url(carte["url"])
    # Même recherche sans largeur (fiche du lieu) : le cache garde la grande photo.
    fiche = client.get("/explorer-image?query=Lac+Rose").get_json()["images"][0]
    assert fiche["url"] == GRANDE and fiche["display_url"] == image_proxy_url(GRANDE)


def test_une_largeur_inconnue_ne_change_rien():
    image = _client().get("/explorer-image?query=Lac+Rose&w=9999").get_json()["images"][0]
    assert image["url"] == GRANDE


def test_l_accueil_demande_la_petite_vignette():
    assert "'&w=500'" in home_source()
