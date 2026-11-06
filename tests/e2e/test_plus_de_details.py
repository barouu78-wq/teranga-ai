"""V5 « réponses courtes » : sous la dernière réponse, un bouton « Plus de détails » (Go du propriétaire, 6 novembre 2026).

L'IA donne d'abord l'essentiel en quelques lignes ; qui veut la suite touche le bouton, qui envoie la question
« Plus de détails » avec la conversation, comme si on l'avait tapée. Le bouton ne reste que sous la dernière réponse,
et pas sous la réponse détaillée elle-même.
"""

import json


def stream(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def ask(page, text):
    page.fill("#input", text)
    page.click("#send")


def _chat_qui_repond(page, base_url, reponses):
    """Chaque appel à /chat reçoit la réponse suivante de la liste ; les corps envoyés sont gardés."""
    corps = []

    def repondre(route):
        corps.append(json.loads(route.request.post_data or "{}"))
        texte = reponses[min(len(corps), len(reponses)) - 1]
        route.fulfill(body=stream({"d": texte}), content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", repondre)
    return corps


def test_plus_de_details_envoie_la_question_avec_la_conversation(page, base_url):
    corps = _chat_qui_repond(page, base_url, ["L'essentiel en trois lignes.", "Le détail complet, étape par étape."])
    page.goto(base_url + "/")
    ask(page, "Comment refaire ma carte d'identité ?")
    page.get_by_text("L'essentiel en trois lignes.").wait_for(timeout=5000)
    bouton = page.get_by_role("button", name="Plus de détails")
    bouton.wait_for(timeout=5000)
    assert bouton.count() == 1
    box = bouton.bounding_box()
    assert box and box["height"] >= 44  # zone tactile (AGENTS.md)

    bouton.click()
    page.get_by_text("Le détail complet, étape par étape.").wait_for(timeout=5000)
    assert len(corps) == 2
    assert corps[1]["message"] == "Plus de détails"
    contenus = [m["content"] for m in corps[1]["history"]]
    assert "Comment refaire ma carte d'identité ?" in contenus and "L'essentiel en trois lignes." in contenus
    # La question apparaît comme une question tapée, et le bouton ne revient pas sous la réponse détaillée.
    assert page.locator(".msg.user .bubble", has_text="Plus de détails").count() == 1
    page.wait_for_timeout(200)
    assert page.get_by_role("button", name="Plus de détails").count() == 0
    assert page.errors == []


def test_le_bouton_ne_reste_que_sous_la_derniere_reponse(page, base_url):
    _chat_qui_repond(page, base_url, ["Première réponse.", "Deuxième réponse."])
    page.goto(base_url + "/")
    ask(page, "Que voir à Saint-Louis ?")
    page.get_by_text("Première réponse.").wait_for(timeout=5000)
    page.get_by_role("button", name="Plus de détails").wait_for(timeout=5000)
    ask(page, "Et pour manger ?")
    page.get_by_text("Deuxième réponse.").wait_for(timeout=5000)
    page.get_by_role("button", name="Plus de détails").wait_for(timeout=5000)
    assert page.get_by_role("button", name="Plus de détails").count() == 1
    derniere = page.locator(".msg.assistant").last
    assert derniere.get_by_role("button", name="Plus de détails").count() == 1
    assert page.errors == []


def test_en_anglais_le_bouton_dit_more_details(page, base_url):
    corps = _chat_qui_repond(page, base_url, ["Short answer.", "Long answer."])
    page.goto(base_url + "/?lang=en")
    ask(page, "How do I get a SIM card?")
    page.get_by_text("Short answer.").wait_for(timeout=5000)
    page.get_by_role("button", name="More details").click()
    page.get_by_text("Long answer.").wait_for(timeout=5000)
    assert corps[1]["message"] == "More details"
    assert page.errors == []


def test_le_bouton_revient_apres_un_rechargement(page, base_url):
    """Relecture Codex de #576 : la conversation gardée pendant la visite revient au rechargement, son bouton aussi."""
    corps = _chat_qui_repond(page, base_url, ["Réponse avant rechargement.", "Suite détaillée."])
    page.goto(base_url + "/")
    ask(page, "Que voir à Gorée ?")
    page.get_by_text("Réponse avant rechargement.").wait_for(timeout=5000)
    page.wait_for_timeout(400)  # enregistrement différé de la conversation
    page.reload()
    page.get_by_text("Réponse avant rechargement.").wait_for(timeout=5000)
    bouton = page.locator(".msg.assistant").last.get_by_role("button", name="Plus de détails")
    bouton.wait_for(timeout=5000)
    bouton.click()
    page.get_by_text("Suite détaillée.").wait_for(timeout=5000)
    assert corps[-1]["message"] == "Plus de détails"
    page.wait_for_timeout(400)
    page.reload()
    page.get_by_text("Suite détaillée.").wait_for(timeout=5000)
    page.wait_for_timeout(200)
    # Après la réponse détaillée, pas de bouton : ni sous elle, ni sous l'ancienne réponse.
    assert page.get_by_role("button", name="Plus de détails").count() == 0
    assert page.errors == []
