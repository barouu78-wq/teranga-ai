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


def test_unknown_address_with_a_line_break_is_a_404_not_a_server_error():
    import os

    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    import app as app_module

    client = app_module.app.test_client()
    # Sondes d'injection d'en-tête (« %0d%0a ») : la majuscule pousse le site à chercher la
    # version en minuscules, qui existe, puis à rediriger vers une adresse contenant le saut de ligne.
    for path in ("/LIEUX/goree%0d%0aX-Test:1", "/Static/a%0Ab", "/Lieux/a%0Db"):
        response = client.get(path, base_url="https://teranga-ai.fr")
        assert response.status_code in (301, 404), (path, response.status_code)
        assert "\n" not in response.headers.get("Location", "") and "\r" not in response.headers.get("Location", "")


def test_project_goal_uses_french_thousands_separators():
    from services.youth_projects import build_project_brief

    brief = build_project_brief(idea="Vendre du jus de bissap", budget_fcfa="500 000 FCFA", goal_fcfa="2 millions")
    assert "500 000 FCFA" in brief["next_action"]
    assert brief["tracking"]["objective"] == "Atteindre 2 000 000 FCFA."


def test_redirect_target_never_returns_control_characters():
    from services.error_pages import redirect_target

    assert redirect_target("/LIEUX/goree\r\nX", lambda p: True) == ""
    assert redirect_target("/Lieux/a\x00b", lambda p: True) == ""
    assert redirect_target("/LIEUX/goree", lambda p: True) == "/lieux/goree"
