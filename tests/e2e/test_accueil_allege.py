"""Accueil allégé sur iPhone (390 px) : peu de boutons, les guides s'ouvrent d'un geste (tests/test_accueil_allege.py)."""

# checkVisibility : les liens d'un <details> fermé ont encore une boîte, mais ne s'affichent pas.
VISIBLES = """() => [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary')]
  .filter(e => { const r = e.getBoundingClientRect();
                 return e.checkVisibility({visibilityProperty: true}) && r.width > 2 && r.height > 2; }).length"""


def test_l_accueil_garde_peu_de_boutons_et_les_guides_s_ouvrent(page, base_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/")
    page.locator("#heroChips button").first.wait_for()
    # 49 boutons et liens avant l'allègement (23 novembre 2026) : en-tête, question, thèmes, CV, WhatsApp, onglets…
    assert page.evaluate(VISIBLES) <= 22
    assert not page.get_by_role("link", name="Dakar", exact=True).is_visible()
    guides = page.locator("details.guide-section summary")
    guides.scroll_into_view_if_needed()
    assert guides.bounding_box()["height"] >= 44
    guides.click()
    assert page.get_by_role("link", name="Dakar", exact=True).is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.errors == []
