"""V5, étape 2 « un écran plus simple » : l'accueil sur téléphone comme la maquette (« Go accueil » du propriétaire,
7 novembre 2026).

La question d'abord, puis « Je suis… » (les cinq profils), puis « Thèmes rapides » : les thèmes du profil (dix pour
« Tout le Sénégal »). Un thème de « Tout le Sénégal » ouvre trois questions fréquentes ; en toucher une la pose. Pendant
les JOJ, la carte des Jeux passe sous les thèmes, sur une ligne. Les couleurs ne changent pas.

En wolof, pas de questions fréquentes inventées : le thème pose directement sa question, comme avant.
"""

import datetime
import json

PHONE = {"width": 390, "height": 844}
FINIES = """() => document.getAnimations().filter((a) => a.effect && a.effect.getComputedTiming().iterations !== Infinity)
  .every((a) => a.playState === 'finished')"""


def _boite(page, selecteur):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect();"
                         " return {top: r.top, bottom: r.bottom, height: r.height}; }", selecteur)


def _accueil(page, base_url, jour=datetime.datetime(2026, 10, 5, 11, 0), chemin="/"):
    page.set_viewport_size(PHONE)
    page.clock.install(time=jour)
    page.add_init_script("localStorage.setItem('teranga-voice', '0')")
    page.goto(base_url + chemin)
    page.locator("#heroInput").wait_for(timeout=5000)
    page.wait_for_function(FINIES, timeout=5000)


def _chat(page, base_url):
    corps = []

    def repondre(route):
        corps.append(route.request.post_data_json)
        route.fulfill(body=json.dumps({"d": "Réponse du thème."}) + "\n", content_type="application/x-ndjson")

    page.route(f"{base_url}/chat", repondre)
    return corps


def test_la_question_d_abord_puis_les_profils_puis_les_themes(page, base_url):
    _accueil(page, base_url)
    question, je_suis = _boite(page, "#heroAsk"), _boite(page, "#audienceLabel")
    profils, themes_titre, themes = _boite(page, "#audienceMode"), _boite(page, "#topicsTitle"), _boite(page, "#heroChips")
    assert question["bottom"] <= je_suis["top"] <= profils["top"], (question, je_suis, profils)
    assert profils["bottom"] <= themes_titre["top"] <= themes["top"], (profils, themes_titre, themes)
    assert page.get_by_text("Je suis…").is_visible() and page.get_by_role("heading", name="Thèmes rapides").is_visible()
    assert page.locator("#heroChips button").count() == 10
    assert themes["bottom"] <= _boite(page, "#stage")["bottom"]  # les dix thèmes tiennent dans le premier écran
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
    assert page.errors == []


def test_un_theme_ouvre_trois_questions_frequentes_et_en_pose_une(page, base_url):
    corps = _chat(page, base_url)
    _accueil(page, base_url)
    sante = page.locator("#heroChips button", has_text="Santé")
    assert sante.get_attribute("aria-expanded") == "false"
    sante.click()
    assert sante.get_attribute("aria-expanded") == "true"
    panneau = page.locator("#themeQs")
    assert panneau.is_visible() and "Santé : questions fréquentes" in panneau.inner_text()
    questions = panneau.get_by_role("button")
    assert questions.count() == 3
    assert all(questions.nth(i).bounding_box()["height"] >= 44 for i in range(3))
    # Le panneau défile jusqu'à l'écran : la dernière question reste au-dessus de la barre d'onglets.
    page.wait_for_function("""() => document.querySelector('#themeQsList button:last-child').getBoundingClientRect().bottom
                              <= document.getElementById('stage').getBoundingClientRect().bottom + 1""", timeout=3000)
    # La première question est celle que le thème posait avant.
    assert questions.first.inner_text() == sante.get_attribute("data-q")
    assert corps == []  # ouvrir un thème ne pose rien
    questions.nth(1).click()
    page.get_by_text("Réponse du thème.").wait_for(timeout=5000)
    assert corps[0]["message"] == "Comment se protéger du paludisme ?" and corps[0]["audience"] == "general"
    assert page.errors == []


def test_chaque_theme_en_francais_et_en_anglais_a_trois_questions_dont_la_sienne(page, base_url):
    for chemin in ("/", "/?lang=en"):
        _accueil(page, base_url, chemin=chemin)
        themes = page.locator("#heroChips button")
        assert themes.count() == 10, chemin
        for i in range(10):
            theme = themes.nth(i)
            theme.click()
            questions = page.locator("#themeQsList button")
            assert questions.count() == 3, (chemin, theme.inner_text())
            assert questions.first.inner_text() == theme.get_attribute("data-q"), (chemin, theme.inner_text())
            theme.click()  # referme avant le thème suivant
    assert page.errors == []


def test_un_autre_theme_remplace_le_panneau_et_le_meme_le_referme(page, base_url):
    _accueil(page, base_url)
    page.locator("#heroChips button", has_text="Papiers").click()
    page.locator("#heroChips button", has_text="Électricité").click()
    assert "Électricité : questions fréquentes" in page.locator("#themeQs").inner_text()
    assert page.locator('#heroChips button[aria-expanded="true"]').count() == 1
    page.locator("#heroChips button", has_text="Électricité").click()
    assert not page.locator("#themeQs").is_visible()
    assert page.locator('#heroChips button[aria-expanded="true"]').count() == 0
    assert page.errors == []


def test_changer_de_profil_referme_le_panneau_et_les_themes_du_profil_posent_leur_question(page, base_url):
    corps = _chat(page, base_url)
    _accueil(page, base_url)
    page.locator("#heroChips button", has_text="Argent").click()
    page.locator('.audience-btn[data-audience="tourist"]').click()
    assert not page.locator("#themeQs").is_visible()
    assert page.locator("#heroChips button").count() == 10
    premier = page.locator("#heroChips button").first
    question = premier.get_attribute("data-q")
    premier.click()
    page.get_by_text("Réponse du thème.").wait_for(timeout=5000)
    assert corps[0]["message"] == question and corps[0]["audience"] == "tourist"
    assert page.errors == []


def test_en_anglais(page, base_url):
    _accueil(page, base_url, chemin="/?lang=en")
    assert page.get_by_text("I am…").is_visible() and page.get_by_role("heading", name="Quick topics").is_visible()
    page.locator("#heroChips button", has_text="Health").click()
    assert "Health: common questions" in page.locator("#themeQs").inner_text()
    assert page.locator("#themeQs").get_by_role("button").count() == 3
    assert page.errors == []


def test_en_wolof_le_theme_pose_sa_question_sans_questions_inventees(page, base_url):
    corps = _chat(page, base_url)
    _accueil(page, base_url, chemin="/?lang=wo")
    premier = page.locator("#heroChips button").first
    assert premier.get_attribute("aria-expanded") is None
    question = premier.get_attribute("data-q")
    premier.click()
    page.get_by_text("Réponse du thème.").wait_for(timeout=5000)
    assert corps[0]["message"] == question
    assert page.errors == []


def test_pendant_les_jeux_la_carte_passe_sous_les_themes_sur_une_ligne(page, base_url):
    _accueil(page, base_url, jour=datetime.datetime(2026, 11, 7, 11, 0))
    assert page.evaluate("document.body.dataset.fete") == "joj"
    carte, themes = _boite(page, "#jojCard"), _boite(page, "#heroChips")
    assert carte["top"] >= themes["bottom"], (carte, themes)
    assert 44 <= carte["height"] <= 80, carte
    assert _boite(page, "#heroAsk")["bottom"] <= _boite(page, "#stage")["bottom"]
    assert page.errors == []
