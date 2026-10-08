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


from services.text import clean_answer  # noqa: E402


def test_clean_answer_keeps_multiplication_signs():
    calcul = "Calcul : 2 adultes * 3 nuits * 45 000 FCFA = 270 000 FCFA"
    assert clean_answer(calcul) == calcul
    # Le vrai italique est toujours retiré, y compris collé à la ponctuation.
    assert clean_answer("Un *très* beau lieu, *vraiment*.") == "Un très beau lieu, vraiment."
    # Les puces en « * » deviennent des « • ».
    assert clean_answer("* Plage\n* Marché") == "• Plage\n• Marché"


def test_clean_answer_keeps_underscores_inside_identifiers():
    # Identifiants, adresses e-mail et noms de fichier contiennent des « _ » qui ne sont pas de l'italique.
    assert clean_answer("Instagram : @teranga_ai_sn") == "Instagram : @teranga_ai_sn"
    assert clean_answer("Écris à jean_pierre_diop@exemple.sn") == "Écris à jean_pierre_diop@exemple.sn"
    assert clean_answer("Fichier ma_liste_courses.pdf") == "Fichier ma_liste_courses.pdf"
    # Le vrai italique en « _ » est toujours retiré.
    assert clean_answer("Un mot _souligné_ ici (_aussi_).") == "Un mot souligné ici (aussi)."
