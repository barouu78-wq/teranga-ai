"""Régressions de l'audit de code : chaque test décrit une entrée réelle qui donnait un résultat faux."""

import io
import json

from services.images import fetch_google_images


def _google_item(title, thumbnail, page):
    return {
        "title": title,
        "link": "https://img.example/" + title.replace(" ", "-") + ".jpg",
        "image": {"thumbnailLink": thumbnail, "contextLink": page},
    }


def _google_photos(items):
    body = json.dumps({"items": items}).encode()
    return fetch_google_images(
        "Dakar", "k", "cx", limit=4, urlopen_fn=lambda req, timeout=8: io.BytesIO(body)
    )


def test_google_thumbnails_are_told_apart_by_their_query_string():
    # Google renvoie des vignettes « …/images?q=tbn:<identifiant> » : tout ce qui
    # distingue deux photos est dans la requête, pas dans le chemin.
    base = "https://encrypted-tbn0.gstatic.com/images?q=tbn:"
    photos = _google_photos([
        _google_item("Corniche de Dakar", base + "AAA", "https://a.example/dakar-1"),
        _google_item("Plateau de Dakar", base + "BBB", "https://a.example/dakar-2"),
        _google_item("Marché de Dakar", base + "CCC", "https://a.example/dakar-3"),
    ])
    assert [p["alt"] for p in photos] == ["Corniche de Dakar", "Plateau de Dakar", "Marché de Dakar"]


def test_google_same_thumbnail_twice_is_still_deduplicated():
    thumb = "https://encrypted-tbn0.gstatic.com/images?q=tbn:AAA"
    photos = _google_photos([
        _google_item("Corniche de Dakar", thumb, "https://a.example/dakar-1"),
        _google_item("Corniche de Dakar (copie)", thumb, "https://b.example/dakar-1"),
    ])
    assert [p["alt"] for p in photos] == ["Corniche de Dakar"]
