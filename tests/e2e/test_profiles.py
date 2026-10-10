"""Les quatre profils de l'accueil (Touriste, Résident, Diaspora, Commerçant) dans un vrai navigateur.

`test_clicks.py` vérifie déjà qu'un profil s'active et que ses suggestions s'affichent. Ici, on vérifie ce que le
navigateur fait réellement du profil : il l'envoie au chat avec la question, le garde après un rechargement,
le transmet au planificateur de voyage, et les quatre boutons restent utilisables sur un téléphone de 390 px.
"""

import json

import pytest

from .test_clicks import PLAN, _fill_planner, ask, stream

PROFILES = ["tourist", "resident", "diaspora", "merchant"]


def _chat_recorder(page, base_url, answer="Réponse du profil."):
    bodies = []

    def handler(route):
        bodies.append(route.request.post_data_json)
        route.fulfill(body=stream({"d": answer}), content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", handler)
    return bodies


def _first_suggestion(page):
    chip = page.locator("#heroChips button").first
    chip.wait_for(timeout=3000)
    return chip.get_attribute("data-q")


@pytest.mark.parametrize("audience", PROFILES)
def test_each_profile_sends_its_audience_and_its_suggestion_to_the_chat(page, base_url, audience):
    bodies = _chat_recorder(page, base_url)
    page.goto(base_url + "/")
    page.locator(f'.audience-btn[data-audience="{audience}"]').click()
    question = _first_suggestion(page)
    page.locator("#heroChips button").first.click()
    page.get_by_text("Réponse du profil.").wait_for(timeout=5000)
    assert len(bodies) == 1
    assert bodies[0]["audience"] == audience
    assert bodies[0]["message"] == question
    assert bodies[0]["language"] == "fr"
    assert page.errors == []


def test_the_four_profiles_do_not_share_the_same_suggestions(page, base_url):
    page.goto(base_url + "/")
    seen = {}
    for audience in PROFILES:
        page.locator(f'.audience-btn[data-audience="{audience}"]').click()
        _first_suggestion(page)
        seen[audience] = tuple(b.get_attribute("data-q") for b in page.locator("#heroChips button").all())
        assert len(seen[audience]) == 4, audience
    assert len(set(seen.values())) == 4, seen
    # Aucune suggestion n'est reprise telle quelle d'un profil à l'autre en tête de liste.
    assert len({questions[0] for questions in seen.values()}) == 4


@pytest.mark.parametrize("audience", PROFILES)
def test_profile_survives_a_reload_and_is_still_sent_to_the_chat(page, base_url, audience):
    bodies = _chat_recorder(page, base_url)
    page.goto(base_url + "/")
    page.locator(f'.audience-btn[data-audience="{audience}"]').click()
    page.reload()
    assert page.locator(f'.audience-btn[data-audience="{audience}"]').get_attribute("aria-pressed") == "true"
    others = [p for p in PROFILES if p != audience]
    assert all(page.locator(f'.audience-btn[data-audience="{p}"]').get_attribute("aria-pressed") == "false" for p in others)
    ask(page, "Bonjour")
    page.get_by_text("Réponse du profil.").wait_for(timeout=5000)
    assert bodies[0]["audience"] == audience
    assert page.errors == []


@pytest.mark.parametrize("saved", ["pirate", "", "TOURIST ", "__proto__", "constructor"])
def test_an_unknown_saved_profile_falls_back_to_tourist(page, base_url, saved):
    """Une valeur périmée ou altérée dans le stockage ne doit ni vider les suggestions ni partir telle quelle au serveur."""
    bodies = _chat_recorder(page, base_url)
    page.add_init_script(f"try{{localStorage.setItem('teranga-audience',{json.dumps(saved)})}}catch(_){{}}")
    page.goto(base_url + "/")
    assert page.locator('.audience-btn[data-audience="tourist"]').get_attribute("aria-pressed") == "true"
    assert len(page.locator("#heroChips button").all()) == 4
    ask(page, "Bonjour")
    page.get_by_text("Réponse du profil.").wait_for(timeout=5000)
    assert bodies[0]["audience"] == "tourist"
    assert page.errors == []


@pytest.mark.parametrize("audience", PROFILES)
def test_profile_is_carried_to_the_trip_planner(page, base_url, audience):
    sent = []

    def planner(route):
        sent.append(json.loads(route.request.post_data))
        route.fulfill(json=PLAN)

    page.route(f"{base_url}/api/trip-planner", planner)
    page.goto(base_url + "/")
    page.locator(f'.audience-btn[data-audience="{audience}"]').click()
    page.locator("#journeyStrip [data-journey='travel']").click()
    page.wait_for_url(f"**/trip-planner?*audience={audience}*", timeout=5000)
    _fill_planner(page)
    page.locator("#result", has_text="Marché central").wait_for(timeout=5000)
    assert sent and sent[0]["audience"] == audience
    assert page.errors == []


def test_profile_buttons_are_comfortable_to_tap_on_a_phone(page, base_url):
    """La rangée des profils défile en horizontal sur téléphone : chaque bouton doit rester atteignable et assez grand."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")  # la page ne défile pas de côté
    for audience in PROFILES:
        button = page.locator(f'.audience-btn[data-audience="{audience}"]')
        assert button.is_visible(), audience
        assert button.evaluate("el => el.tagName") == "BUTTON"
        box = button.bounding_box()
        assert box["height"] >= 44 and box["width"] >= 44, (audience, box)  # zone tactile minimale
        assert box["x"] >= 0 and min(box["x"] + box["width"], 390) - box["x"] >= 44, (audience, box)  # au moins 44 px visibles
        button.scroll_into_view_if_needed()
        button.click()
        assert button.get_attribute("aria-pressed") == "true", audience
    assert page.errors == []
