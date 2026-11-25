"""Dates du planificateur lues comme un billet d'avion : départ, puis retour (tests/test_trip_planner.py).

Propriétaire, 24 novembre 2026 : « mettre c'est quand le départ et c'est quand la personne rentre ». Sur sa capture,
l'ancienne page (« Arrivée », puis « Départ ») laissait un départ le 24 novembre avant une arrivée le 27.
"""

STEP = "section.step.active"


def _ouvrir(page, base_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/trip-planner")
    assert page.locator("label.field").nth(0).inner_text().startswith("Départ")
    assert page.locator("label.field").nth(1).inner_text().startswith("Retour")


def test_le_retour_suit_le_depart_et_le_nombre_de_jours_s_affiche(page, base_url):
    _ouvrir(page, base_url)
    # Comme sur la capture : une date choisie d'abord en bas, puis un départ plus tard.
    page.fill("input[name=departure]", "2026-11-24")
    page.fill("input[name=arrival]", "2026-11-27")
    # Le retour ne reste pas avant le départ : il passe une semaine après, visible et modifiable.
    assert page.input_value("input[name=departure]") == "2026-12-04"
    assert page.locator("#tripDays").inner_text() == "7 jours d'activités"
    page.fill("input[name=departure]", "2026-11-30")
    assert page.locator("#tripDays").inner_text() == "3 jours d'activités"
    page.fill("input[name=departure]", "2026-11-28")
    assert page.locator("#tripDays").inner_text() == "1 jour d'activités"
    assert page.locator("#status").inner_text() == ""
    page.click(f"{STEP} [data-next]")
    assert page.locator(STEP).get_attribute("data-step") == "2"
    assert page.errors == []


def test_un_retour_avant_le_depart_est_signale_tout_de_suite(page, base_url):
    _ouvrir(page, base_url)
    page.fill("input[name=arrival]", "2026-11-24")
    assert page.input_value("input[name=departure]") == "2026-12-01"
    page.fill("input[name=departure]", "2026-11-20")
    # La date que la personne vient de choisir n'est pas changée en douce : on lui dit pourquoi ça ne va pas.
    assert page.input_value("input[name=departure]") == "2026-11-20"
    assert page.locator("#status").inner_text() == "La date de retour doit être après la date de départ."
    assert page.locator("#tripDays").inner_text() == ""
    page.click(f"{STEP} [data-next]")
    assert page.locator(STEP).get_attribute("data-step") == "1"
    page.fill("input[name=departure]", "2026-11-26")
    assert page.locator("#status").inner_text() == ""
    assert page.locator("#tripDays").inner_text() == "2 jours d'activités"
    assert page.errors == []


def test_en_anglais_departure_puis_return(page, base_url):
    page.goto(base_url + "/trip-planner?lang=en")
    assert page.locator("label.field").nth(0).inner_text().startswith("Departure")
    assert page.locator("label.field").nth(1).inner_text().startswith("Return")
    page.fill("input[name=arrival]", "2026-11-24")
    assert page.locator("#tripDays").inner_text() == "7 days of activities"
    assert page.errors == []


def test_un_lien_partage_affiche_aussi_le_nombre_de_jours(page, base_url):
    from .test_clicks import _shared_trip_url

    page.goto(_shared_trip_url(base_url))  # du 1er au 4 novembre
    page.wait_for_selector(".day-card")
    assert page.locator("#tripDays").inner_text() == "3 jours d'activités"
    assert page.errors == []
