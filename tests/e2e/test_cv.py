"""Mon CV dans un vrai navigateur (téléphone, 390 px) : « Go emploi » du 15 novembre 2026.

Le parcours part à /api/cv (réponse simulée ici), le CV revient dans un modèle, se corrige dans l'aperçu, reste dans
ce navigateur après un rechargement, et « Télécharger en PDF » lance l'impression. Le texte de l'IA n'est jamais
interprété comme du HTML.
"""

import json
import re

from playwright.sync_api import expect

CV = {
    "nom": "Awa Ndiaye", "titre": "Comptable", "ville": "Dakar", "telephone": "", "email": "",
    "profil": "Comptable avec trois ans d'expérience.",
    "experiences": [{"poste": "Aide-comptable", "employeur": "Entreprise", "lieu": "Dakar", "dates": "2023 – 2026",
                     "taches": ["Saisie des factures", "<img src=x onerror=window.piege=1>"]}],
    "formations": [{"diplome": "BTS Comptabilité", "etablissement": "École", "dates": "2023"}],
    "competences": ["Sage", "Excel"], "langues": ["Français", "Wolof"],
    "lettre": "Madame, Monsieur,\n\nJe souhaite rejoindre votre équipe.", "a_verifier": ["Préciser le nom de l'école"],
    "manque": ["Permis B"], "alerte": "",
}


def ouvrir(page, base_url, envois):
    def repondre(route):
        envois.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(body=json.dumps({"cv": CV}), content_type="application/json")

    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/api/cv", repondre)
    page.add_init_script("window.__imprime = 0; window.print = () => { window.__imprime += 1; };")
    page.goto(base_url + "/cv")


def test_un_parcours_devient_un_cv_modifiable_garde_sur_le_telephone(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.fill("#cvPoste", "Comptable")
    page.fill("#cvOffre", "Recrute comptable, permis B souhaité.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert envois[-1] == {"poste": "Comptable", "offre": "Recrute comptable, permis B souhaité.",
                          "parcours": "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar."}
    feuille = page.locator("#cvFeuille")
    assert feuille.get_by_text("Awa Ndiaye").is_visible() and feuille.get_by_text("Saisie des factures").is_visible()
    # Le texte de l'IA reste du texte : aucune balise créée, aucun script lancé.
    assert feuille.get_by_text("<img src=x onerror=window.piege=1>").is_visible()
    assert page.evaluate("document.querySelectorAll('#cvFeuille img').length === 0 && !window.piege")
    assert page.get_by_text("Permis B").is_visible() and page.locator("#cvLettre").get_by_text("Je souhaite rejoindre").is_visible()
    # Modèle Moderne, puis correction dans l'aperçu.
    page.get_by_role("button", name="Moderne").click()
    assert "moderne" in feuille.get_attribute("class")
    nom = feuille.get_by_text("Awa Ndiaye")
    nom.click()
    page.keyboard.press("End")
    page.keyboard.type(" Sow")
    page.get_by_role("button", name="Télécharger en PDF").click()
    assert page.evaluate("window.__imprime") == 1
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    # Rechargé : le CV corrigé et le modèle reviennent, sans nouvel appel.
    page.reload()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert page.locator("#cvFeuille").get_by_text("Awa Ndiaye Sow").is_visible()
    assert "moderne" in page.locator("#cvFeuille").get_attribute("class")
    assert len(envois) == 1


def test_un_cv_en_pdf_part_avec_le_poste_et_recommencer_efface_tout(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    page.set_input_files("#cvFichier", files=[{"name": "mon-cv.pdf", "mimeType": "application/pdf",
                                               "buffer": b"%PDF-1.4\n%%EOF\n"}])
    page.get_by_text("Fichier prêt : mon-cv.pdf").wait_for()
    page.fill("#cvPoste", "Comptable")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert envois[-1]["fichier"]["nom"] == "mon-cv.pdf" and envois[-1]["fichier"]["type"] == "application/pdf"
    page.get_by_role("button", name="Recommencer").click()
    assert page.locator("#cvResultat").is_hidden() and page.locator("#cvForm").is_visible()
    page.reload()
    assert page.locator("#cvResultat").is_hidden()


def test_sans_cv_ni_parcours_rien_ne_part(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_text("Choisis ton CV : PDF, Word ou photo.").wait_for()
    assert envois == []


def test_les_modeles_a_colonne_passent_sur_deux_colonnes_sur_grand_ecran(page, base_url):
    # La largeur se lit sur le bloc qui contient la feuille : une requête de conteneur ne s'applique jamais à
    # l'élément conteneur lui-même (défaut vu le 15 novembre 2026, colonnes seulement en PDF).
    envois = []
    ouvrir(page, base_url, envois)
    page.set_viewport_size({"width": 1100, "height": 900})
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    colonnes = "getComputedStyle(document.getElementById('cvFeuille')).gridTemplateColumns.split(' ').length"
    for nom, attendu in (("Moderne", 2), ("Océan", 2), ("Élégant", 2), ("Sobre", 1), ("Créatif", 1)):
        page.get_by_role("button", name=nom, exact=True).click()
        assert page.evaluate(colonnes) == attendu, nom
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="Moderne", exact=True).click()
    assert page.evaluate(colonnes) == 1


LONG = dict(
    CV, nom="Fatou Diop", titre="Vendeuse", ville="Mbour",
    profil=("Vendeuse avec une licence en gestion administrative. A tenu seule un commerce de tissus : accueil et "
            "conseil des clients, suivi des stocks, approvisionnement auprès des fournisseurs et organisation des ventes. "
            "Utilise Word, Excel et Photoshop au quotidien."),
    experiences=[
        {"poste": "Gérante", "employeur": "Commerce de tissus", "lieu": "Mbour", "dates": "2023 – 2024",
         "taches": ["Accueillait et conseillait les clients.", "Organisait les ventes et les promotions du marché.",
                    "Suivait les stocks et préparait les commandes.", "Assurait l'approvisionnement auprès des fournisseurs.",
                    "Gérait l'administration et les finances de l'activité.", "Tenait le cahier des ventes chaque soir."]},
        {"poste": "Stagiaire, secrétariat général", "employeur": "Mairie", "lieu": "Mbour", "dates": "Mars – juin 2022",
         "taches": ["Élaborait les bordereaux administratifs.", "Traitait les ordres de recettes.",
                    "Soumettait les dossiers pour signature et en assurait le suivi.",
                    "Vérifiait et mettait en conformité les documents après signature.",
                    "Classait et archivait les dossiers du service.", "Accueillait et orientait les usagers."]},
        {"poste": "Vendeuse saisonnière", "employeur": "Boutique de prêt-à-porter", "lieu": "Dakar", "dates": "2021",
         "taches": ["Conseillait la clientèle en rayon.", "Tenait la caisse et les encaissements.",
                    "Mettait en place les vitrines."]},
        {"poste": "Animatrice bénévole", "employeur": "Association de quartier", "lieu": "Mbour", "dates": "2018 – 2020",
         "taches": ["Organisait les activités des jeunes le samedi.", "Tenait la liste des inscrits.",
                    "Préparait les réunions mensuelles."]},
    ],
    formations=[
        {"diplome": "Licence en gestion administrative des entreprises et collectivités locales",
         "etablissement": "Université", "dates": "2019 – 2022"},
        {"diplome": "Baccalauréat L", "etablissement": "Lycée", "dates": "2017 – 2018"},
        {"diplome": "BFEM", "etablissement": "Collège", "dates": "2014"},
    ],
    competences=["Accueil, conseil et relation clientèle", "Suivi des stocks et approvisionnement",
                 "Organisation des ventes", "Word : courriers et rapports", "Excel : tableaux et formules",
                 "Photoshop : supports de communication"],
    langues=["Français", "Wolof", "Anglais (notions)"],
)


def pages_pdf(page):
    # Pages du PDF que Chromium imprimerait (format et marges de la règle @page du site).
    return len(re.findall(rb"/Type\s*/Page(?!s)", page.pdf(prefer_css_page_size=True, print_background=True)))


def test_un_cv_un_peu_long_tient_sur_une_page_a4(page, base_url):
    # Vu le 15 novembre 2026 sur le PDF du propriétaire (modèle Élégant) : une seule ligne de formation passait en
    # page 2, avec un morceau de la colonne. Le CV est réduit juste assez, au moment du PDF, pour tenir sur une page.
    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/api/cv", lambda route: route.fulfill(body=json.dumps({"cv": LONG}), content_type="application/json"))
    page.add_init_script("window.print = () => { window.__echelle = getComputedStyle(document.getElementById('cvFeuille'))"
                         ".getPropertyValue('--cv-echelle').trim(); };")
    page.goto(base_url + "/cv")
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "Licence en gestion, gérante d'un commerce de tissus à Mbour, stage à la mairie.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    page.get_by_role("button", name="Élégant", exact=True).click()
    page.get_by_role("button", name="Télécharger en PDF").click()
    echelle = page.evaluate("window.__echelle")
    assert echelle and 0.8 <= float(echelle) < 1
    # window.print est simulé : on attend la fin du mode impression, puis on le remet à la main pour le PDF.
    expect(page.locator("body")).not_to_have_class(re.compile("imprime-cv"))
    page.emulate_media(media="print")
    page.evaluate("document.body.classList.add('imprime-cv')")
    assert pages_pdf(page) == 2  # sans réduction, le CV déborde bien
    page.evaluate(f"document.getElementById('cvFeuille').style.setProperty('--cv-echelle', '{echelle}')")
    assert pages_pdf(page) == 1


def test_la_lettre_seule_sort_sur_une_page(page, base_url):
    # Le reste de la page, même invisible, ajoutait des pages blanches au PDF.
    envois = []
    ouvrir(page, base_url, envois)
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.fill("#cvOffre", "Recrute comptable, permis B souhaité.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    page.emulate_media(media="print")
    page.evaluate("document.body.classList.add('imprime-lettre')")
    assert pages_pdf(page) == 1


def test_un_cv_court_n_est_pas_reduit(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    page.add_init_script("window.print = () => { window.__echelle = getComputedStyle(document.getElementById('cvFeuille'))"
                         ".getPropertyValue('--cv-echelle').trim(); };")
    page.reload()
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    page.get_by_role("button", name="Télécharger en PDF").click()
    assert page.evaluate("window.__echelle") in ("", "1")
