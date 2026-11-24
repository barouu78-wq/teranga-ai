"""Mon CV dans un vrai navigateur (téléphone, 390 px) : « Go emploi » du 15 novembre 2026.

Le parcours part à /api/cv (réponse simulée ici), le CV revient dans un modèle, se corrige dans l'aperçu, reste dans
ce navigateur après un rechargement, et « Télécharger en PDF » lance l'impression. Le texte de l'IA n'est jamais
interprété comme du HTML.
"""

import json
import re

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
    page.get_by_text("J’ai déjà un CV").click()  # le départ par défaut est le parcours depuis le 23 novembre 2026
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
    page.get_by_role("button", name="Créer mon CV").click()  # départ par défaut : le parcours
    page.locator("#cvErreur").get_by_text("Raconte ton parcours en quelques phrases.").wait_for()
    page.get_by_text("J’ai déjà un CV").click()
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
    # Import ici : le job pytest du CI n'installe pas Playwright, il doit pouvoir lire ce fichier et l'ignorer.
    from playwright.sync_api import expect

    expect(page.locator("body")).not_to_have_class(re.compile("imprime-cv"))
    page.emulate_media(media="print")
    page.evaluate("document.body.classList.add('imprime-cv')")
    assert pages_pdf(page) == 2  # sans réduction, le CV déborde bien
    page.evaluate(f"document.getElementById('cvFeuille').style.setProperty('--cv-echelle', '{echelle}')")
    assert pages_pdf(page) == 1


# CV du propriétaire (24 novembre 2026, modèle Océan) : 5 expériences et 12 compétences sortaient sur 2 pages, une date
# en bas de la page 1 et son poste en haut de la page 2. Réduire jusqu'à 70 % le fait tenir sur une page.
PLUS_LONG = dict(LONG, experiences=LONG["experiences"] + [
    {"poste": "Stagiaire en maintenance", "employeur": "Collège", "lieu": "Thiès", "dates": "Octobre 2014",
     "taches": ["Contrôlait les structures et les réseaux.", "Remplaçait l'appareillage défectueux.",
                "Rangeait l'atelier.", "Tenait le registre des interventions."]},
], competences=LONG["competences"] + ["Gestion des stocks et inventaires", "Préparation de commandes",
                                      "Contrôle des prix et des promotions", "PowerPoint", "AutoCAD", "Permis B (en cours)"])


def test_un_cv_tres_long_tient_aussi_sur_une_page(page, base_url):
    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/api/cv",
               lambda route: route.fulfill(body=json.dumps({"cv": PLUS_LONG}), content_type="application/json"))
    page.add_init_script("window.print = () => { window.__echelle = getComputedStyle(document.getElementById('cvFeuille'))"
                         ".getPropertyValue('--cv-echelle').trim(); };")
    page.goto(base_url + "/cv")
    page.fill("#cvParcours", "BTS management commercial, quatre ans en rayon, intérim de conseiller de vente.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    page.get_by_role("button", name="Océan", exact=True).click()
    page.get_by_role("button", name="Télécharger en PDF").click()
    echelle = page.evaluate("window.__echelle")
    assert echelle and 0.7 <= float(echelle) < 0.8, echelle
    from playwright.sync_api import expect

    expect(page.locator("body")).not_to_have_class(re.compile("imprime-cv"))
    page.emulate_media(media="print")
    page.evaluate("document.body.classList.add('imprime-cv')")
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


def test_les_contacts_et_les_rubriques_portent_une_icone_decorative(page, base_url):
    # « Go icônes » du 18 novembre 2026 : icônes Lucide (licence ISC) dans l'en-tête et devant chaque rubrique,
    # dessinées par cv.js (aucun fichier ni script d'un autre site), ignorées par les lecteurs d'écran.
    page.route(f"{base_url}/api/cv", lambda r: r.fulfill(
        body=json.dumps({"cv": dict(CV, telephone="77 000 00 00", email="awa@exemple.sn")}), content_type="application/json"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/cv")
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    feuille = page.locator("#cvFeuille")
    contacts = feuille.locator(".cv-contact li")
    assert contacts.count() == 3
    for i, icone in enumerate(("ville", "telephone", "email")):
        assert contacts.nth(i).locator(f"svg.cv-ico[data-icone='{icone}'][aria-hidden='true']").count() == 1
    rubriques = feuille.locator(".cv-rubrique")
    assert rubriques.count() >= 4
    for i in range(rubriques.count()):
        assert rubriques.nth(i).locator("svg.cv-ico[aria-hidden='true']").count() == 1, rubriques.nth(i).inner_text()
    # Le texte reste lisible et copiable tel quel : l'icône n'ajoute aucun caractère.
    assert contacts.nth(1).inner_text().strip() == "77 000 00 00"
    page.get_by_role("button", name="Élégant", exact=True).click()
    assert feuille.locator(".cv-rubrique svg.cv-ico").count() == rubriques.count()


def test_l_exemple_de_cv_fini_mene_au_formulaire_et_s_efface_quand_mon_cv_est_pret(page, base_url):
    from playwright.sync_api import expect

    envois = []
    ouvrir(page, base_url, envois)
    exemple = page.locator("#cvExemple")
    assert exemple.get_by_text("personne fictive").is_visible()
    feuille = page.locator("#cvExempleFeuille")
    feuille.get_by_text("Assistante comptable").wait_for()
    # Même rendu que le vrai CV (icônes comprises), mais rien à modifier : ce n'est pas le CV de la personne.
    assert feuille.locator("svg.cv-ico").count() >= 5
    assert feuille.locator("[contenteditable]").count() == 0
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("link", name="Faire le mien").click()
    expect(page.locator("#cvForm")).to_be_in_viewport()
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert exemple.is_hidden()
    page.reload()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert exemple.is_hidden()
    page.get_by_role("button", name="Recommencer").click()
    assert exemple.is_visible()


def test_les_etapes_du_formulaire_sont_signalees_une_fois_chacune(page, base_url):
    """« Go 1 » du 23 novembre 2026 : savoir où les visiteurs s'arrêtent. Chaque étape part une seule fois par visite,
    sans rien de ce que la personne écrit dans l'adresse."""
    envois, etapes = [], []
    page.on("request", lambda req: etapes.append(req.url.split("/cv/etape/", 1)[1]) if "/cv/etape/" in req.url else None)
    ouvrir(page, base_url, envois)
    page.get_by_role("link", name="Faire le mien").click()
    page.get_by_text("J’ai déjà un CV").click()
    with page.expect_file_chooser():
        page.get_by_role("button", name="Créer mon CV").click()  # sans fichier : refusé, le choix du fichier s'ouvre
    page.get_by_text("Choisis ton CV : PDF, Word ou photo.").wait_for()
    with page.expect_file_chooser():
        page.get_by_role("button", name="Créer mon CV").click()  # deuxième refus : pas de nouveau signal
    page.set_input_files("#cvFichier", files=[{"name": "cv.txt", "mimeType": "text/plain", "buffer": b"texte"}])
    page.get_by_text("Ce type de fichier n’est pas accepté").wait_for()
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "Trop court")
    page.get_by_role("button", name="Créer mon CV").click()
    page.locator("#cvErreur").get_by_text("Raconte ton parcours en quelques phrases.").wait_for()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    page.wait_for_timeout(300)  # les signaux partent sans attendre de réponse
    assert sorted(etapes) == sorted(["faire-le-mien", "debut", "refus-fichier", "fichier-refuse", "refus-parcours",
                                     "envoi"]), etapes
    assert len(envois) == 1


def test_envoyer_a_un_ami_est_compte_une_fois_sans_rien_du_cv(page, base_url):
    """« Go parrainage » du 24 novembre 2026 : savoir si quelqu'un partage. Le clic sur « Envoyer à un ami sur
    WhatsApp » compte l'étape « partage » une fois par visite ; WhatsApp ne reçoit que l'adresse de /cv."""
    envois, etapes = [], []
    page.on("request", lambda req: etapes.append(req.url.split("/cv/etape/", 1)[1]) if "/cv/etape/" in req.url else None)
    page.context.route("https://wa.me/**", lambda route: route.fulfill(body="ok"))
    ouvrir(page, base_url, envois)
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    for _ in range(2):
        with page.context.expect_page() as onglet:
            page.get_by_role("link", name="Envoyer à un ami sur WhatsApp").click()
        assert "Ndiaye" not in onglet.value.url and "comptabilit" not in onglet.value.url
        onglet.value.close()
    page.wait_for_timeout(300)  # le signal part sans attendre de réponse
    assert etapes.count("partage") == 1, etapes


def test_sans_cv_le_nom_et_trois_lignes_suffisent(page, base_url):
    """Départ par défaut (« Go 1 » du 23 novembre 2026) : pas de fichier à chercher. Le nom part en tête du parcours."""
    envois = []
    ouvrir(page, base_url, envois)
    assert page.locator("#cvParcours").is_visible() and page.locator("#cvNom").is_visible()
    assert page.locator("#cvBlocFichier").is_hidden()
    page.fill("#cvNom", "Awa Ndiaye")
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.fill("#cvPoste", "Comptable")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert envois[-1]["parcours"] == "Nom : Awa Ndiaye\nBTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar."
    # Recommencer revient au départ par défaut, nom compris.
    page.get_by_role("button", name="Recommencer").click()
    assert page.locator("#cvParcours").is_visible() and page.locator("#cvBlocFichier").is_hidden()
    assert page.input_value("#cvNom") == ""


def test_cliquer_creer_sans_toucher_un_champ_n_est_pas_un_debut(page, base_url):
    """Relecture Codex (#644) : « debut » veut dire « premier champ touché » ; le clic sur « Créer mon CV » seul n'en
    est pas un."""
    envois, etapes = [], []
    page.on("request", lambda req: etapes.append(req.url.split("/cv/etape/", 1)[1]) if "/cv/etape/" in req.url else None)
    ouvrir(page, base_url, envois)
    page.get_by_role("button", name="Créer mon CV").click()
    page.locator("#cvErreur").wait_for()
    page.wait_for_timeout(300)
    assert "debut" not in etapes, etapes
    page.get_by_text("Je n’ai pas de CV").click()
    page.wait_for_timeout(300)
    assert etapes.count("debut") == 1, etapes


def test_le_bouton_du_formulaire_reste_visible_au_dessus_du_bandeau_des_cookies(page, base_url, monkeypatch):
    """Constat du 23 novembre 2026 : sur téléphone, le visiteur venu d'une annonce voyait le bandeau « Cookies
    publicitaires » recouvrir « Faire le mien », placé sous l'exemple. Un bouton sous le titre reste visible."""
    import app as app_module
    from services.google_ads_tag import google_ads_config

    monkeypatch.setitem(app_module.app.config, "GOOGLE_ADS", google_ads_config("AW-18578242897"))
    page.route("https://www.googletagmanager.com/**", lambda route: route.fulfill(content_type="text/javascript", body=""))
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base_url + "/cv")
    bandeau = page.locator(".teranga-ads-consent-panel")
    bandeau.wait_for()
    bouton = page.locator(".cv-hero a[href='#cvForm']")
    haut_bandeau = bandeau.bounding_box()["y"]
    boite = bouton.bounding_box()
    assert boite["y"] + boite["height"] <= haut_bandeau
    bouton.click()
    assert page.evaluate("location.hash") == "#cvForm"
    assert page.errors == []


def test_le_bouton_du_titre_disparait_avec_le_formulaire_et_revient_avec_recommencer(page, base_url):
    """Relecture Codex (#653) : un CV gardé sur le téléphone cache le formulaire ; le bouton du titre, qui y mène,
    doit disparaître aussi au lieu de rester sans effet, puis revenir avec « Recommencer »."""
    envois = []
    ouvrir(page, base_url, envois)
    bouton = page.locator(".cv-hero a[href='#cvForm']")
    assert bouton.is_visible()
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert not bouton.is_visible()
    page.reload()  # CV restauré depuis le téléphone
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    assert not bouton.is_visible()
    page.get_by_role("button", name="Recommencer").click()
    assert bouton.is_visible()
    assert page.errors == []


TITRES = """() => [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
  .filter(h => h.getBoundingClientRect().height > 0).map(h => +h.tagName[1])"""


def test_les_titres_du_cv_ne_sautent_pas_de_niveau(page, base_url):
    """Audit d'accessibilité du 23 novembre 2026 : les rubriques du CV (Profil, Expérience…) étaient des h4 sous un
    h2, un saut de niveau qui gêne la navigation au lecteur d'écran. Vrai pour l'exemple et pour le CV créé."""
    envois = []
    ouvrir(page, base_url, envois)
    def sans_saut():
        niveaux = page.evaluate(TITRES)
        assert niveaux.count(1) == 1
        assert all(b <= a + 1 for a, b in zip(niveaux, niveaux[1:])), niveaux

    sans_saut()  # exemple de CV
    page.get_by_text("Je n’ai pas de CV").click()
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    sans_saut()  # CV créé
    # Les rubriques gardent leur style de CV (12 px), pas celui des titres « À vérifier » (17 px).
    tailles = page.evaluate("""() => [...document.querySelectorAll('#cvFeuille .cv-rubrique')]
      .map(h => getComputedStyle(h).fontSize)""")
    assert tailles and set(tailles) == {"12px"}, tailles
    assert page.errors == []


def test_le_resultat_reste_court_et_le_pdf_toujours_a_portee(page, base_url):
    """Remarque du propriétaire (24 novembre 2026, iPhone) : « La page est longue... ». Les 9 modèles tiennent sur une
    ligne qui défile, et « Télécharger en PDF » reste visible pendant qu'on lit le CV."""
    ouvrir(page, base_url, [])
    page.fill("#cvParcours", "BTS comptabilité en 2023, puis trois ans d'aide-comptable à Dakar.")
    page.get_by_role("button", name="Créer mon CV").click()
    page.get_by_role("heading", name="Ton CV est prêt").wait_for()
    modeles = page.locator(".cv-modeles").bounding_box()
    assert modeles["height"] < 64, modeles  # une seule ligne de boutons (44 px)
    page.get_by_role("button", name="Élégant").scroll_into_view_if_needed()
    page.get_by_role("button", name="Élégant").click()
    assert "elegant" in page.locator("#cvFeuille").get_attribute("class")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    # Au milieu du CV, le bouton de téléchargement est à l'écran.
    page.locator("#cvFeuille").get_by_text("Saisie des factures").scroll_into_view_if_needed()
    page.evaluate("window.scrollBy(0, 200)")
    pdf = page.locator("#cvPdf").bounding_box()
    assert 0 <= pdf["y"] and pdf["y"] + pdf["height"] <= 844, pdf
