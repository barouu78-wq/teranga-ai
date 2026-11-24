"""Profil envoyé par l'accueil, dans un vrai navigateur.

Jusqu'au 23 novembre 2026, l'accueil proposait « Je suis… » (Tout le Sénégal, Touriste, Résident, Diaspora,
Commerçant). Accueil allégé (tests/test_accueil_allege.py) : plus de choix, l'accueil envoie toujours « Tout le
Sénégal » (general) au chat et au planificateur, même si un ancien choix reste dans le navigateur.
"""

import json

import pytest

from .test_clicks import PLAN, _fill_planner, ask, stream


def _chat_recorder(page, base_url, answer="Réponse du profil."):
    bodies = []

    def handler(route):
        bodies.append(route.request.post_data_json)
        route.fulfill(body=stream({"d": answer}), content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", handler)
    return bodies


def test_le_premier_theme_part_au_chat_avec_le_profil_general(page, base_url):
    bodies = _chat_recorder(page, base_url)
    page.goto(base_url + "/")
    chip = page.locator("#heroChips button").first
    chip.wait_for(timeout=3000)
    assert page.locator("#heroChips button").count() == 4
    chip.click()  # un thème ouvre ses questions fréquentes (V5) ; la première est sa question
    question = page.locator("#themeQsList button").first
    attendu = question.get_attribute("data-q")
    question.click()
    page.get_by_text("Réponse du profil.").wait_for(timeout=5000)
    assert len(bodies) == 1
    assert bodies[0]["audience"] == "general" and bodies[0]["message"] == attendu and bodies[0]["language"] == "fr"
    assert page.errors == []


@pytest.mark.parametrize("saved", ["tourist", "merchant", "pirate", "__proto__"])
def test_un_ancien_profil_garde_dans_le_navigateur_n_est_plus_envoye(page, base_url, saved):
    """Sans bouton pour en changer, un ancien « Touriste » resterait caché : l'accueil ne le lit plus."""
    bodies = _chat_recorder(page, base_url)
    page.add_init_script(f"try{{localStorage.setItem('teranga-audience',{json.dumps(saved)})}}catch(_){{}}")
    page.goto(base_url + "/")
    assert page.locator(".audience-btn").count() == 0
    ask(page, "Bonjour")
    page.get_by_text("Réponse du profil.").wait_for(timeout=5000)
    assert bodies[0]["audience"] == "general"
    assert page.errors == []


def test_le_planificateur_recoit_le_profil_general(page, base_url):
    sent = []

    def planner(route):
        sent.append(json.loads(route.request.post_data))
        route.fulfill(json=PLAN)

    page.route(f"{base_url}/api/trip-planner", planner)
    page.goto(base_url + "/")
    page.locator("#journeyStrip [data-journey='travel']").click()
    page.wait_for_url("**/trip-planner?*audience=general*", timeout=5000)
    _fill_planner(page)
    page.locator("#result", has_text="Marché central").wait_for(timeout=5000)
    assert sent and sent[0]["audience"] == "general"
    assert page.errors == []
