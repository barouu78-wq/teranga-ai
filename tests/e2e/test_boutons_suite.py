"""Boutons de suite (version 9) : sous la dernière réponse, les suggestions que le serveur envoie déjà.

Le serveur joint à chaque réponse jusqu'à 3 suggestions (`ux.followups`, services/intelligence.py) que la page
n'affichait pas. Un appui pose la suggestion comme nouvelle question ; « Préciser ma demande » remet le curseur
dans la zone de saisie sans rien envoyer. Les réponses de `/chat` sont simulées : aucun appel réseau.
"""

import json

import pytest

TRANSPORT = {"intent": "transport", "show_followups": True,
             "followups": ["Itinéraire à Dakar", "Prix à Dakar", "Alternative à Dakar"]}


def stream(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def ask(page, text):
    page.fill("#input", text)
    page.click("#send")


def chat_route(page, base_url, answers):
    """Sert les réponses dans l'ordre et garde le message envoyé à chaque appel."""
    sent = []
    queue = iter(answers)

    def handler(route):
        sent.append(json.loads(route.request.post_data or "{}").get("message"))
        route.fulfill(body=stream(*next(queue)), content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", handler)
    return sent


def followups(page):
    return page.locator(".followups button")


def test_suggestions_appear_under_the_answer_and_ask_the_question(page, base_url):
    sent = chat_route(page, base_url, [
        ({"d": "Réponse sur le transport."}, {"ux": TRANSPORT}),
        ({"d": "Voici les repères de prix."},),
    ])
    page.goto(base_url + "/")
    ask(page, "Comment aller à Dakar ?")
    page.get_by_text("Réponse sur le transport.").wait_for(timeout=5000)
    assert followups(page).all_inner_texts() == ["Itinéraire à Dakar", "Prix à Dakar", "Alternative à Dakar"]
    assert page.get_attribute(".followups", "role") == "group"
    for button in followups(page).all():
        assert button.bounding_box()["height"] >= 44  # zone tactile
    followups(page).nth(1).click()
    page.get_by_text("Voici les repères de prix.").wait_for(timeout=5000)
    assert sent == ["Comment aller à Dakar ?", "Prix à Dakar"]
    assert followups(page).count() == 0  # la 2e réponse n'a pas de suggestion : l'ancienne rangée a disparu
    assert page.errors == []


def test_clarify_puts_the_cursor_back_and_sends_nothing(page, base_url):
    ux = {"intent": "general_information", "show_followups": True,
          "followups": ["Préciser ma demande", "Comparer", "Que faire ensuite ?"]}
    sent = chat_route(page, base_url, [({"d": "Réponse générale."}, {"ux": ux})])
    page.goto(base_url + "/")
    ask(page, "Parle-moi du Sénégal")
    page.get_by_text("Réponse générale.").wait_for(timeout=5000)
    page.get_by_role("button", name="Préciser ma demande").click()
    assert page.evaluate("document.activeElement && document.activeElement.id") == "input"
    page.wait_for_timeout(300)
    assert sent == ["Parle-moi du Sénégal"]
    assert page.errors == []


def test_only_the_latest_answer_keeps_its_suggestions(page, base_url):
    chat_route(page, base_url, [
        ({"d": "Première réponse."}, {"ux": TRANSPORT}),
        ({"d": "Deuxième réponse."}, {"ux": TRANSPORT}),
    ])
    page.goto(base_url + "/")
    ask(page, "Comment aller à Dakar ?")
    page.get_by_text("Première réponse.").wait_for(timeout=5000)
    ask(page, "Et le soir ?")
    page.get_by_text("Deuxième réponse.").wait_for(timeout=5000)
    assert page.locator(".followups").count() == 1
    assert followups(page).count() == 3
    assert page.errors == []


@pytest.mark.parametrize("ux", [
    None,
    {"intent": "transport", "show_followups": False, "followups": ["Prix à Dakar"]},
    {"intent": "transport", "show_followups": True, "followups": []},
    {"intent": "transport", "show_followups": True, "followups": "Prix à Dakar"},
])
def test_no_suggestion_row_without_usable_suggestions(page, base_url, ux):
    events = [{"d": "Réponse sans suite."}] + ([{"ux": ux}] if ux is not None else [])
    chat_route(page, base_url, [tuple(events)])
    page.goto(base_url + "/")
    ask(page, "Bonjour")
    page.get_by_text("Réponse sans suite.").wait_for(timeout=5000)
    assert page.locator(".followups").count() == 0
    assert page.errors == []


def test_english_page_translates_suggestions_and_skips_unknown_ones(page, base_url):
    ux = {"intent": "transport", "show_followups": True,
          "followups": ["Prix à Dakar", "Un libellé inconnu", "Comparer"]}
    sent = chat_route(page, base_url, [({"d": "Transport answer."}, {"ux": ux}), ({"d": "Prices answer."},)])
    page.goto(base_url + "/")
    page.click("#langs button[data-lang='en']")
    ask(page, "How do I get to Dakar?")
    page.get_by_text("Transport answer.").wait_for(timeout=5000)
    assert followups(page).all_inner_texts() == ["Prices in Dakar", "Compare"]
    assert page.get_attribute(".followups", "aria-label") == "To continue"
    followups(page).first.click()
    page.get_by_text("Prices answer.").wait_for(timeout=5000)
    assert sent[-1] == "Prices in Dakar"
    assert page.errors == []
