"""Chaque bouton important répond à un vrai clic."""

import json

import pytest

PAGES = ["/", "/trip-planner", "/explorer", "/regions/dakar", "/visiter-goree", "/en/senegal-travel-guide", "/lieux/goree"]


def stream(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def ask(page, text):
    page.fill("#input", text)
    page.click("#send")


@pytest.mark.parametrize("path", PAGES)
def test_pages_load_without_js_errors(page, base_url, path):
    response = page.goto(base_url + path)
    assert response.status == 200
    page.wait_for_timeout(300)
    assert page.errors == []


def test_chat_answers_and_send_works_twice(page, base_url):
    answers = iter(["Bonjour de Dakar !", "Deuxième réponse."])
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=stream({"d": next(answers)}), content_type="application/x-ndjson"))
    page.goto(base_url + "/")
    ask(page, "Bonjour")
    page.get_by_text("Bonjour de Dakar !").wait_for(timeout=5000)
    ask(page, "Et ensuite ?")
    page.get_by_text("Deuxième réponse.").wait_for(timeout=5000)
    assert page.errors == []


def test_chat_error_offers_working_retry(page, base_url):
    calls = []

    def handler(route):
        calls.append(1)
        if len(calls) == 1:
            route.fulfill(status=503, json={"error": "Service indisponible."}, headers={"Retry-After": "1"})
        else:
            route.fulfill(body=stream({"d": "Réponse après relance."}), content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", handler)
    page.goto(base_url + "/")
    ask(page, "Bonjour")
    retry = page.locator("#messages button", has_text="Réessayer")
    retry.first.wait_for(timeout=5000)
    retry.first.click()
    page.get_by_text("Réponse après relance.").wait_for(timeout=5000)


def test_chat_works_when_browser_storage_is_blocked(page, base_url):
    page.add_init_script(
        "for (const k of ['localStorage','sessionStorage'])"
        " Object.defineProperty(window, k, {get(){throw new DOMException('bloqué','SecurityError')}});"
    )
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=stream({"d": "Ça marche quand même."}), content_type="application/x-ndjson"))
    page.goto(base_url + "/")
    ask(page, "Bonjour")
    page.get_by_text("Ça marche quand même.").wait_for(timeout=5000)
    assert page.errors == []


def test_theme_and_language_buttons_respond(page, base_url):
    page.goto(base_url + "/")
    before = page.evaluate("document.body.dataset.theme || ''")
    page.click("#themeBtn")
    assert page.evaluate("document.body.dataset.theme || ''") != before
    page.click("#langs button[data-lang='en']")
    assert page.get_attribute("#langs button[data-lang='en']", "aria-pressed") == "true"
    assert page.get_attribute("html", "lang") == "en"


def test_project_form_recovers_from_network_failure(page, base_url):
    page.route(f"{base_url}/api/projects/plan", lambda r: r.abort())
    page.goto(base_url + "/")
    page.click("#journeyStrip button[data-journey='project']")
    page.fill("#projectIdea", "Vendre du jus de bissap à Thiès")
    page.click("#projectSubmit")
    page.locator("#projectError", has_text="Service indisponible").wait_for(timeout=5000)
    assert page.is_enabled("#projectSubmit")


def _fill_planner(page):
    page.fill("input[name='arrival']", "2026-12-01")
    page.fill("input[name='departure']", "2026-12-02")
    for _ in range(4):
        page.locator("section.step.active [data-next]").click()
    page.locator("section.step.active button[type='submit']").click()


PLAN = {
    "plan": {
        "summary": "Deux jours à Kaolack.",
        "days": [
            {"day": 1, "title": "Arrivée", "region": "Kaolack", "morning": "Marché central", "afternoon": "Repos", "evening": "Dîner", "transport": "Taxi"},
            {"day": 2, "title": "Saloum", "region": "Kaolack", "morning": "Pirogue", "afternoon": "Plage", "evening": "Retour", "transport": "Bus"},
        ],
        "practical_notes": [],
    },
    "map_html": "",
}


def test_trip_planner_generates_plan(page, base_url):
    page.route(f"{base_url}/api/trip-planner", lambda r: r.fulfill(json=PLAN))
    page.goto(base_url + "/trip-planner")
    _fill_planner(page)
    page.locator("#result", has_text="Marché central").wait_for(timeout=5000)
    assert page.errors == []


def test_trip_planner_error_releases_button(page, base_url):
    page.route(f"{base_url}/api/trip-planner", lambda r: r.fulfill(status=503, json={"error": "Service momentanément indisponible."}))
    page.goto(base_url + "/trip-planner")
    _fill_planner(page)
    page.locator("#status", has_text="indisponible").wait_for(timeout=5000)
    assert page.locator("section.step.active button[type='submit']").is_enabled()


def test_share_button_copies_link(page, base_url):
    page.goto(base_url + "/visiter-goree")
    page.evaluate("delete Navigator.prototype.share")
    page.click("#share-page")
    page.locator("#share-page", has_text="Lien copié").wait_for(timeout=3000)
    assert page.evaluate("navigator.clipboard.readText()").endswith("/visiter-goree")


def test_trip_planner_copy_link_button(page, base_url):
    page.route(f"{base_url}/api/trip-planner", lambda r: r.fulfill(json=PLAN))
    page.goto(base_url + "/trip-planner")
    _fill_planner(page)
    page.locator("#result", has_text="Marché central").wait_for(timeout=5000)
    page.click("#copy")
    assert "#trip=" in page.evaluate("navigator.clipboard.readText()")
