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
    assert page.get_attribute("#themeBtn", "data-mode") == "auto"
    page.click("#themeBtn")
    assert page.get_attribute("#themeBtn", "data-mode") == "light"
    assert page.evaluate("document.body.dataset.theme") == "light"
    page.click("#themeBtn")
    assert page.evaluate("document.body.dataset.theme") == "dark"
    page.reload()
    assert page.evaluate("document.body.dataset.theme") == "dark"  # choix mémorisé
    page.click("#themeBtn")
    assert page.get_attribute("#themeBtn", "data-mode") == "auto"
    page.click("#langs button[data-lang='en']")
    assert page.get_attribute("#langs button[data-lang='en']", "aria-pressed") == "true"
    assert page.get_attribute("html", "lang") == "en"
    assert page.errors == []


@pytest.mark.parametrize("when,theme", [("2026-10-05T10:00:00", "light"), ("2026-10-05T20:30:00", "dark"), ("2026-10-06T04:00:00", "dark")])
def test_auto_theme_follows_time_of_day(page, base_url, when, theme):
    import datetime

    page.clock.install(time=datetime.datetime.fromisoformat(when))
    page.goto(base_url + "/")
    assert page.evaluate("document.body.dataset.theme") == theme
    page.goto(base_url + "/visiter-goree")
    assert page.evaluate("document.documentElement.dataset.theme") == theme


def test_old_saved_theme_no_longer_blocks_auto_mode(page, base_url):
    import datetime

    # Avant, un simple clic enregistrait « light » et figeait le thème.
    page.add_init_script("if(!localStorage.getItem('teranga-theme-v'))localStorage.setItem('teranga-theme','light')")
    page.clock.install(time=datetime.datetime.fromisoformat("2026-10-05T21:00:00"))
    page.goto(base_url + "/")
    assert page.get_attribute("#themeBtn", "data-mode") == "auto"
    assert page.evaluate("document.body.dataset.theme") == "dark"
    page.click("#themeBtn")
    page.reload()
    assert page.get_attribute("#themeBtn", "data-mode") == "light"  # un nouveau choix est gardé
    assert page.errors == []


def test_festive_touch_on_independence_day(page, base_url):
    import datetime

    page.clock.install(time=datetime.datetime(2027, 4, 4, 11, 0))
    page.goto(base_url + "/")
    assert page.evaluate("document.body.dataset.fete") == "independance"
    assert "Indépendance" in page.text_content("#feteBanner")
    page.goto(base_url + "/?fete=tabaski")
    assert page.evaluate("document.body.dataset.fete") == "tabaski"


def test_project_plan_is_built_inside_the_chat(page, base_url):
    page.route(f"{base_url}/chat", lambda r: r.fulfill(
        body=stream({"d": "Bonne idée : commence petit."}, {"ux": {"intent": "project", "mode": "action"}}),
        content_type="application/x-ndjson"))
    calls = []

    def plan(route):
        calls.append(1)
        if len(calls) == 1:
            route.abort()
        else:
            route.fulfill(json={"project": {"name": "Jus de bissap", "city": "Thiès", "category": "food",
                                            "next_action": "Faire goûter 20 personnes",
                                            "steps": [{"title": "Tester", "action": "Vendre 10 bouteilles"}]}})

    page.route(f"{base_url}/api/projects/plan", plan)
    page.goto(base_url + "/")
    assert page.locator("#journeyStrip button[data-journey='project']").count() == 0
    ask(page, "Je veux vendre du jus de bissap à Thiès")
    offer = page.locator(".project-offer-btn")
    offer.wait_for(timeout=5000)
    offer.click()
    page.locator(".project-offer .project-error", has_text="Service indisponible").wait_for(timeout=5000)
    assert offer.is_enabled()
    offer.click()
    page.locator(".project-offer-result", has_text="Faire goûter 20 personnes").wait_for(timeout=5000)
    assert page.locator(".project-offer-result a[href^='/opportunities']").count() == 1
    assert page.errors == []


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


def test_trip_planner_reads_streamed_plan(page, base_url):
    body = stream({"progress": {"day": 0, "total": 2}}, {"progress": {"day": 1, "total": 2}}, {"result": PLAN})
    seen = {}

    def handler(route):
        seen["stream"] = route.request.headers.get("x-teranga-stream")
        route.fulfill(body=body, content_type="application/x-ndjson")

    page.route(f"{base_url}/api/trip-planner", handler)
    page.goto(base_url + "/trip-planner")
    _fill_planner(page)
    page.locator("#result", has_text="Pirogue").wait_for(timeout=5000)
    assert seen["stream"] == "1"
    assert page.errors == []


def test_trip_planner_stream_error_is_shown(page, base_url):
    body = stream({"progress": {"day": 0, "total": 2}}, {"error": "La génération a pris trop de temps.", "status": 504})
    page.route(f"{base_url}/api/trip-planner", lambda r: r.fulfill(body=body, content_type="application/x-ndjson"))
    page.goto(base_url + "/trip-planner")
    _fill_planner(page)
    page.locator("#status", has_text="trop de temps").wait_for(timeout=5000)
    assert page.locator("section.step.active button[type='submit']").is_enabled()


def test_report_button_sends_question_and_answer(page, base_url):
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=stream({"d": "Réponse à signaler."}), content_type="application/x-ndjson"))
    sent = {}

    def report(route):
        sent.update(json.loads(route.request.post_data))
        route.fulfill(json={"ok": True})

    page.route(f"{base_url}/api/report", report)
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(base_url + "/")
    ask(page, "Question test")
    page.get_by_text("Réponse à signaler.").wait_for(timeout=5000)
    page.locator(".acts button.report").first.click()
    page.locator(".acts button.report", has_text="Signalé").wait_for(timeout=5000)
    assert sent == {"question": "Question test", "reply": "Réponse à signaler.", "reason": "inappropriate"}


def test_offline_mode_keeps_visited_guides_and_explains_chat(browser):
    import threading

    from werkzeug.serving import make_server

    from app import app

    # Serveur propre au test : on l'arrête pour couper vraiment le réseau
    # (le mode hors ligne simulé de Playwright n'atteint pas le service worker).
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    context = browser.new_context(service_workers="allow")
    context.route(lambda url: not url.startswith(base), lambda route: route.abort())
    page = context.new_page()
    try:
        page.goto(base + "/")
        page.evaluate("navigator.serviceWorker.ready.then(() => true)")
        page.reload()  # la page est maintenant contrôlée par le service worker
        for path in ("/lieux/goree", "/visiter-goree", "/"):
            page.goto(base + path)
        page.wait_for_timeout(300)
        server.shutdown()
        server.server_close()
        context.set_offline(True)
        page.goto(base + "/lieux/goree")
        assert "Gorée" in page.title()
        page.goto(base + "/une-page-jamais-vue")
        assert "Hors ligne" in page.title()
        page.locator("#offline-pages a", has_text="Gorée").first.wait_for(timeout=5000)
        page.goto(base + "/")
        page.fill("#input", "Bonjour")
        page.click("#send")
        page.get_by_text("Tu es hors ligne").wait_for(timeout=5000)
        assert page.locator("#messages a[href='/offline']").count() == 1
    finally:
        context.close()


def test_chat_shows_partner_booking_links_and_drops_foreign_ones(page, base_url):
    places = [{"id": "goree", "name": "Île de Gorée", "book": [
        {"label": "🏨 Hôtels à Dakar", "href": "/go/hotels?q=Dakar&from=goree"},
        {"label": "piège", "href": "https://evil.example/"},
    ]}]
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=stream({"d": "Gorée est une île."}, {"places": places}), content_type="application/x-ndjson"))
    page.goto(base_url + "/")
    ask(page, "Parle-moi de Gorée")
    link = page.get_by_text("🏨 Hôtels à Dakar")
    link.wait_for(timeout=5000)
    assert link.get_attribute("rel") == "sponsored nofollow"
    assert "commission" in link.get_attribute("title")
    assert page.get_by_text("piège").count() == 0
    assert page.errors == []
