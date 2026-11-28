"""« Donner mon avis » en bas de l'accueil, plus dans la rangée de partage (tests/test_avis.py).

Propriétaire, 28 novembre 2026 : « Déplace l'avis dans le bas de page ».
"""


def test_l_avis_est_en_bas_de_l_accueil(page, base_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/")
    assert page.locator(".spread a[href='/avis']").count() == 0
    lien = page.locator(".home-foot a[href='/avis']")
    lien.scroll_into_view_if_needed()
    assert lien.is_visible()
    assert lien.inner_text() == "Donner mon avis"
    box = lien.bounding_box()
    assert box["height"] >= 44
    assert box["y"] > page.locator("#guidesTitle").bounding_box()["y"]
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.errors == []
