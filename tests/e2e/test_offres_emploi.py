"""Offres d'emploi sur téléphone (390 px) : lisible sans défilement de côté, boutons assez grands, chaque site
s'ouvre dans un nouvel onglet (on ne quitte pas Teranga), et le CV est proposé d'abord."""


def test_les_sites_d_offres_s_ouvrent_a_part_sur_un_telephone(page, base_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/offres-emploi")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    liens = page.locator(".emploi-site a")
    assert liens.count() >= 3
    for i in range(liens.count()):
        lien = liens.nth(i)
        assert lien.get_attribute("target") == "_blank"
        assert lien.bounding_box()["height"] >= 44
    page.get_by_role("link", name="Faire mon CV gratuit").click()
    page.wait_for_url("**/cv")
