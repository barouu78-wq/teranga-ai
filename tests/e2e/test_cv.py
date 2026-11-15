"""Mon CV dans un vrai navigateur (téléphone, 390 px) : « Go emploi » du 15 novembre 2026.

Le parcours part à /api/cv (réponse simulée ici), le CV revient dans un modèle, se corrige dans l'aperçu, reste dans
ce navigateur après un rechargement, et « Télécharger en PDF » lance l'impression. Le texte de l'IA n'est jamais
interprété comme du HTML.
"""

import json

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
