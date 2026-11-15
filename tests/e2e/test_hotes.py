"""Teranga Hôtes dans un vrai navigateur (téléphone) : la page de la maison, puis la question dans le chat.

La question choisie sur /hote/<nom> part tout de suite vers le chat, avec la maison (« hote ») pour que le serveur
ajoute ses informations au contexte de l'IA. L'adresse est nettoyée : un rechargement ne la renvoie pas.
"""

import json


def test_une_suggestion_de_la_maison_part_dans_le_chat_avec_la_maison(page, base_url):
    envois = []

    def repondre(route):
        envois.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(body=json.dumps({"d": "Réponse pour la maison."}) + "\n", content_type="application/x-ndjson")

    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/chat", repondre)
    page.goto(base_url + "/hote/exemple")
    assert page.get_by_text("Exemple · établissement fictif").is_visible()
    # Lisible à 390 px : aucun défilement horizontal.
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("link", name="Comment venir depuis l’aéroport ?").click()
    page.get_by_text("Réponse pour la maison.").wait_for()
    assert envois and envois[-1]["hote"] == "exemple"
    assert envois[-1]["message"] == "Comment venir depuis l’aéroport ?"
    assert "q=" not in page.url  # un rechargement ne renvoie pas la question


def test_le_formulaire_de_la_maison_envoie_la_question_ecrite(page, base_url):
    envois = []
    page.route(f"{base_url}/chat", lambda route: (envois.append(json.loads(route.request.post_data or "{}")),
                                                  route.fulfill(body=json.dumps({"d": "Servi de 7 h 30 à 10 h."}) + "\n",
                                                                content_type="application/x-ndjson")))
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/hote/exemple")
    page.fill("#hote-q", "À quelle heure est le petit-déjeuner ?")
    page.get_by_role("button", name="Envoyer la question").click()
    page.get_by_text("Servi de 7 h 30 à 10 h.").wait_for()
    assert envois[-1]["hote"] == "exemple"
