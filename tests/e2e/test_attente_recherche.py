"""Recherche web : « Je cherche des informations à jour… » sous les points, retirée quand la réponse arrive.

La route `/chat` est simulée : aucun appel réseau. Le flux n'envoie que `{"st": "web"}` ; la page redemande alors la
réponse en JSON. Cette réponse est retenue, comme pendant une longue recherche, le temps de vérifier la phrase
d'attente, puis servie.
"""

import json


def test_la_phrase_d_attente_s_affiche_pendant_la_recherche_puis_disparait(page, base_url):
    pending = []

    def handler(route):
        if (route.request.headers.get("x-teranga-mode") or "").lower() == "json":
            pending.append(route)
            return
        route.fulfill(body=json.dumps({"st": "web"}) + "\n", content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", handler)
    page.goto(base_url + "/")
    page.fill("#input", "Quelles sont les dernières nouvelles sur le TER de Dakar ?")
    page.click("#send")

    status = page.locator(".typing-status")
    status.wait_for(timeout=5000)
    assert status.inner_text() == "Je cherche des informations à jour…"
    assert status.get_attribute("role") == "status"
    assert page.locator(".typing").count() == 1  # les points restent : la phrase s'ajoute dessous

    # Attente d'une condition (la demande JSON retenue), pas d'une durée.
    for _ in range(100):
        if pending:
            break
        page.wait_for_timeout(50)
    assert pending, "la page n'a pas redemandé la réponse"
    assert status.is_visible(), "la phrase reste tant que la réponse n'est pas là"
    pending[0].fulfill(body=json.dumps({"reply": "Le TER circule normalement cette semaine."}),
                       content_type="application/json")

    page.get_by_text("Le TER circule normalement cette semaine.").wait_for(timeout=5000)
    assert status.count() == 0
    assert page.locator(".typing").count() == 0
    assert page.errors == []


def test_sans_recherche_aucune_phrase_d_attente(page, base_url):
    page.route(f"{base_url}/chat", lambda route: route.fulfill(
        body=json.dumps({"d": "Le thiéboudienne est le plat national."}) + "\n", content_type="application/x-ndjson"))
    page.goto(base_url + "/")
    page.fill("#input", "C'est quoi le thiéboudienne ?")
    page.click("#send")
    page.get_by_text("Le thiéboudienne est le plat national.").wait_for(timeout=5000)
    assert page.locator(".typing-status").count() == 0
    assert page.errors == []
