"""« Pendant ton séjour » dans un vrai navigateur (tests/test_planificateur_sejour.py).

Les fêtes attendues sont lues dans le calendrier du site (services/events.py), pas recopiées ici : le test suit le
calendrier quand une date lunaire est confirmée ou corrigée.
"""

import datetime as dt

from services.events import events_between

from .test_clicks import PLAN

STEP = "section.step.active"


def _dates(page, base_url, arrival, departure):
    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/api/trip-planner", lambda route: route.fulfill(json=PLAN))
    page.goto(base_url + "/trip-planner")
    page.fill("input[name=arrival]", arrival)
    page.fill("input[name=departure]", departure)


def _generer(page):
    for _ in range(4):
        page.locator(f"{STEP} [data-next]").click()
    page.locator(f"{STEP} button[type='submit']").click()
    page.locator(".day-card").first.wait_for(timeout=5000)


def test_les_fetes_du_sejour_s_affichent_des_les_dates_puis_dans_le_resultat(page, base_url):
    attendues = events_between(dt.date(2027, 4, 30), dt.date(2027, 5, 7))
    assert len(attendues) >= 2, "le calendrier n'a plus de fête entre le 30 avril et le 7 mai 2027 : choisir d'autres dates"
    _dates(page, base_url, "2027-04-30", "2027-05-07")
    ligne = page.locator("#tripEvents").inner_text()
    assert ligne == "Pendant ton séjour : " + ", ".join(e["name"] for e in attendues)
    _generer(page)
    bloc = page.locator(".trip-events-box")
    assert bloc.locator("h3").inner_text() == "Pendant ton séjour"
    assert bloc.locator("li").count() == len(attendues)
    premier = bloc.locator("li").first.inner_text()
    assert attendues[0]["name"] in premier
    assert f"{attendues[0]['start'].day} " in premier and str(attendues[0]["start"].year) in premier
    assert attendues[0]["tips"][:30] in premier
    assert bloc.get_by_role("link", name="Calendrier des fêtes").get_attribute("href") == "/calendrier-fetes-senegal"
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.errors == []


def test_une_date_lunaire_est_marquee_estimee(page, base_url):
    estimees = [e for e in events_between(dt.date(2027, 5, 15), dt.date(2027, 5, 20)) if not e["confirmed"]]
    assert estimees, "plus de fête à date estimée entre le 15 et le 20 mai 2027 : choisir d'autres dates"
    _dates(page, base_url, "2027-05-15", "2027-05-20")
    _generer(page)
    texte = page.locator(".trip-events-box").inner_text()
    assert estimees[0]["name"] in texte
    assert "date estimée, à confirmer" in texte
    assert page.errors == []


def test_sans_fete_rien_ne_s_ajoute(page, base_url):
    assert events_between(dt.date(2026, 11, 15), dt.date(2026, 11, 20)) == []
    _dates(page, base_url, "2026-11-15", "2026-11-20")
    assert not page.locator("#tripEvents").is_visible()
    _generer(page)
    assert page.locator(".trip-events-box").count() == 0
    assert page.errors == []


def test_en_anglais_sans_conseils_en_francais(page, base_url):
    attendues = events_between(dt.date(2027, 4, 30), dt.date(2027, 5, 7))
    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/api/trip-planner", lambda route: route.fulfill(json=PLAN))
    page.goto(base_url + "/trip-planner?lang=en")
    page.fill("input[name=arrival]", "2027-04-30")
    page.fill("input[name=departure]", "2027-05-07")
    assert page.locator("#tripEvents").inner_text().startswith("During your trip: ")
    _generer(page)
    texte = page.locator(".trip-events-box").inner_text()
    assert "May 2027" in texte
    assert attendues[0]["tips"][:30] not in texte
    assert page.errors == []
