"""Page du résultat du planificateur, allégée (tests/test_trip_planner.py).

Accord du propriétaire, 24 novembre 2026 (« Ok parfait retire »), sur six points montrés en capture :
1. le formulaire se cache une fois l'itinéraire prêt, « Modifier mes choix » le rouvre ;
2. plus de boutons Écouter, Transport, Horaires, Prix sous chaque jour (« Écouter » en haut et « Infos pratiques »
   en bas restent) ;
3. plus de petit tracé du trajet (la carte reste) ;
4. plus de liste « Jour 1 Dakar, Jour 2… » ;
5. plus de bouton « Enregistrer les modifications » : les changements s'enregistrent tout seuls ;
6. « Budget indicatif » seulement quand il y a un budget à montrer.
"""

import json

from .test_clicks import PLAN, _fill_planner

RETIRES = "#route-visual, #journey-steps, #save-trip, [data-day-voice], [data-day-practical]"


def _plan(page, base_url, plan=PLAN):
    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/api/trip-planner", lambda route: route.fulfill(json=plan))
    page.goto(base_url + "/trip-planner")
    _fill_planner(page)
    page.locator(".day-card").first.wait_for(timeout=5000)


def test_le_resultat_garde_l_essentiel_sans_les_doublons(page, base_url):
    _plan(page, base_url)
    assert not page.is_visible("#planner")
    assert page.locator(RETIRES).count() == 0
    assert not page.get_by_text("Budget indicatif").is_visible()
    for nom in ("Écouter", "+ Ajouter une journée", "Partager l’itinéraire", "Enregistrer en PDF",
                "Demander à Teranga de revoir mon séjour"):
        assert page.get_by_role("button", name=nom).first.is_visible(), nom
    assert page.locator("#practical").is_visible()
    assert page.locator(".day-card summary").first.inner_text() == "Modifier ce jour"
    # Les choix restent là : « Modifier mes choix » rouvre le formulaire au début, dates comprises.
    page.get_by_role("button", name="Modifier mes choix").click()
    assert page.is_visible("#planner")
    assert page.locator("section.step.active").get_attribute("data-step") == "1"
    assert page.input_value("input[name=arrival]") == "2026-12-01"
    assert not page.get_by_role("button", name="Modifier mes choix").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.errors == []


def test_un_changement_s_enregistre_sans_bouton(page, base_url):
    _plan(page, base_url)
    jour = page.locator(".day-card").first
    jour.locator("summary").click()
    titre = jour.locator(".day-title")
    titre.fill("Pirogue au Saloum")
    titre.blur()
    page.locator(".day-card").nth(1).locator("summary").click()
    page.locator(".day-card").nth(1).locator("[data-remove]").click()
    assert page.locator(".day-card").count() == 1
    # Le lien de partage et la session suivent sans « Enregistrer » : la page rouverte montre le voyage modifié.
    page.reload()
    page.locator(".day-card").first.wait_for(timeout=5000)
    assert page.locator(".day-card").count() == 1
    assert "Pirogue au Saloum" in page.locator(".day-card").first.inner_text()
    saved = json.loads(page.evaluate("sessionStorage.getItem('teranga-trip-plan')"))
    assert [d["title"] for d in saved["days"]] == ["Pirogue au Saloum"]
    assert page.errors == []


def test_le_budget_s_affiche_quand_il_y_en_a_un(page, base_url):
    plan = dict(PLAN, budget={"lines": ["Hébergement : à vérifier selon la saison."]})
    _plan(page, base_url, plan)
    assert page.get_by_text("Budget indicatif").is_visible()
    assert page.get_by_text("Hébergement : à vérifier selon la saison.").is_visible()
    assert page.errors == []


def test_ecouter_et_arreter_marchent_toujours(page, base_url):
    """« Écouter » en haut reste le seul bouton de lecture : il doit marcher (variables de la voix gardées)."""
    page.route(f"{base_url}/tts", lambda route: route.fulfill(status=503, body=""))
    _plan(page, base_url)
    page.get_by_role("button", name="Écouter", exact=True).click()
    page.get_by_role("button", name="Arrêter", exact=True).click()
    page.wait_for_timeout(300)  # laisse la lecture échouer ou s'arrêter : une erreur de script arriverait ici
    assert page.errors == []
