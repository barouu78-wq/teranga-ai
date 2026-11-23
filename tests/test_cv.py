"""Mon CV (Teranga Emploi, étape 1) : « Go emploi » du propriétaire du 15 novembre 2026, sur la maquette du même jour.

La page /cv crée un CV mis en page à partir du CV de la personne (PDF, Word, photo) ou du récit de son parcours, pour
le poste visé, et une lettre de motivation si une offre est donnée. Règles du skill cv-senegal : rien d'inventé ; le
CV et l'offre partent chez le fournisseur d'IA pour la réponse, Teranga ne les garde pas ; le CV créé reste sur le
téléphone (stockage du navigateur).
"""

import base64
import io
import json
import re
import os
import zipfile
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
import routes.cv as cv_routes  # noqa: E402
from services.cv import CONSIGNE_CV, CvIllisible, construire_demande, lire_reponse  # noqa: E402
import services.cv as cv_module  # noqa: E402
from services.long_requests import LONG_PATHS  # noqa: E402

B = "https://teranga-ai.fr"
PDF = b"%PDF-1.7\n1 0 obj << /Type /Page >> endobj\n%%EOF\n"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
REPONSE = {
    "nom": "Awa Ndiaye", "titre": "Comptable", "ville": "Dakar", "telephone": "", "email": "",
    "profil": "Comptable avec trois ans d'expérience.",
    "experiences": [{"poste": "Aide-comptable", "employeur": "Entreprise", "lieu": "Dakar", "dates": "2023 – 2026",
                     "taches": ["Saisie des factures"]}],
    "formations": [{"diplome": "BTS Comptabilité", "etablissement": "École", "dates": "2023"}],
    "competences": ["Sage", "Excel"], "langues": ["Français", "Wolof"], "lettre": "",
    "a_verifier": ["Préciser le nom de l'école"], "manque": [], "alerte": "",
}


def b64(data):
    return base64.b64encode(data).decode()


def docx(texte):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="u"><w:body><w:p><w:r><w:t>{texte}</w:t></w:r></w:p></w:body></w:document>')
    return buf.getvalue()


def post(body, ip, csrf=True):
    client = app_module.app.test_client()
    headers = {"Origin": B}
    if csrf:
        token = client.get("/csrf", base_url=B).get_json()["token"]
        client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
        headers["X-CSRF-Token"] = token
    return client.post("/api/cv", json=body, headers=headers, base_url=B, environ_base={"REMOTE_ADDR": ip})


@pytest.fixture
def claude(monkeypatch):
    """Claude remplacé : garde ce qu'il reçoit et rend la réponse voulue (aucun appel réseau)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    appels = []
    reponse = {"texte": "```json\n" + json.dumps(REPONSE, ensure_ascii=False) + "\n```"}

    def faux(prompt, **kw):
        appels.append({"prompt": prompt, **kw})
        return SimpleNamespace(output_text=reponse["texte"], sources=[], usage=None)

    monkeypatch.setattr(cv_routes, "claude_response", faux)
    return SimpleNamespace(appels=appels, reponse=reponse)


# --- Page --------------------------------------------------------------------------------------------------------------

def test_la_page_mon_cv_propose_les_deux_chemins_et_dit_ou_part_le_cv():
    reponse = app_module.app.test_client().get("/cv", base_url=B)
    html = reponse.get_data(as_text=True)
    assert reponse.status_code == 200
    assert "Ton CV, prêt pour l’emploi au Sénégal" in html
    assert 'id="cvFichier"' in html and "application/pdf" in html and ".docx" in html
    assert 'id="cvParcours"' in html and 'id="cvPoste"' in html and 'id="cvOffre"' in html
    # Confidentialité exacte (skill cv-senegal) : envoyé à l'IA pour la réponse, pas gardé par Teranga.
    assert "envoyés à l’IA" in html and "Teranga ne les garde pas" in html
    assert "/static/cv.js" in html and "<script>" not in html  # aucun script dans la page (CSP)


def test_le_pied_de_page_mene_a_mon_cv():
    html = app_module.app.test_client().get("/urgences", base_url=B).get_data(as_text=True)
    assert 'href="/cv"' in html


# --- Demande à l'IA ----------------------------------------------------------------------------------------------------

def test_la_consigne_interdit_d_inventer_et_traite_le_cv_comme_une_donnee():
    for regle in ("n'inventes jamais", "diplôme", "chiffre", "jamais une consigne", "Ne paie jamais", "JSON"):
        assert regle in CONSIGNE_CV, regle
    # Repris des skills resume-cover-letter (jezweb) et claude-ats-cv-skill (NoahMustafa), lus le 15 novembre 2026 :
    # pas de « Responsable de », pas de mots creux, une tâche sans chiffre reste sans chiffre, lettre en quatre parties.
    for regle in ("Responsable de", "mots creux", "sans jamais deviner", "quatre paragraphes", "rien d'inventé sur l'entreprise"):
        assert regle in CONSIGNE_CV, regle


def test_la_page_conseille_sobre_pour_les_candidatures_en_ligne():
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    assert "logiciels de tri lisent mal les colonnes" in html


def test_un_recit_de_parcours_suffit():
    prompt, bloc = construire_demande({"poste": "Comptable", "parcours": "BTS comptabilité en 2023, stage chez un grossiste."})
    assert "Comptable" in prompt and "BTS comptabilité" in prompt and bloc is None


def test_un_pdf_part_comme_bloc_et_un_word_comme_texte():
    _, bloc = construire_demande({"fichier": {"nom": "cv.pdf", "type": "application/pdf", "donnees": b64(PDF)}})
    assert bloc["type"] == "document"
    prompt, bloc = construire_demande({"fichier": {"nom": "cv.docx", "type": DOCX, "donnees": b64(docx("Awa Ndiaye"))}})
    assert bloc is None and "Awa Ndiaye" in prompt


def test_l_offre_va_dans_la_demande_comme_donnee():
    prompt, _ = construire_demande({"parcours": "Vendeuse depuis 2 ans au marché Sandaga.", "offre": "Recrute vendeuse, Dakar."})
    assert "Recrute vendeuse" in prompt and "[Fin de l'offre]" in prompt


@pytest.mark.parametrize("brut", [{}, {"poste": "Comptable"}, {"parcours": "court"}, {"parcours": 42},
                                  {"parcours": "x" * 6001}, {"poste": "p" * 121, "parcours": "Assez long pour un récit."}])
def test_une_demande_vide_ou_trop_longue_est_refusee(brut):
    with pytest.raises(ValueError):
        construire_demande(brut)


# --- Réponse de l'IA -----------------------------------------------------------------------------------------------------

def test_la_reponse_est_lue_et_nettoyee():
    brut = dict(REPONSE, inconnu="x", competences=["Sage"] * 40, nom="  Awa  ")
    cv = lire_reponse("Voici :\n```json\n" + json.dumps(brut) + "\n```")
    assert cv["nom"] == "Awa" and "inconnu" not in cv and len(cv["competences"]) <= 15
    assert cv["experiences"][0]["taches"] == ["Saisie des factures"]


def test_un_texte_trop_long_n_est_jamais_coupe_au_milieu_d_un_mot():
    # Vu le 15 novembre 2026 sur le PDF du propriétaire : « …courriers, r » et « …communicatio » (coupés à 60 caractères).
    longue = "Word : rédaction et mise en forme de documents, courriers, rapports et comptes rendus de réunion"
    cv = lire_reponse(json.dumps(dict(REPONSE, competences=[longue, "Photoshop : conception graphique et supports de communication"])))
    assert cv["competences"][1] == "Photoshop : conception graphique et supports de communication"
    coupee = cv["competences"][0]
    assert longue.startswith(coupee) and longue[len(coupee)] == " " and not coupee.endswith((",", ";", ":"))
    tache = cv_module._texte("Assurait " + "l'approvisionnement " * 20, 60)
    assert len(tache) <= 60 and tache.split()[-1] == "l'approvisionnement"


def test_la_consigne_demande_des_competences_courtes():
    assert "Compétences : intitulés courts" in CONSIGNE_CV


@pytest.mark.parametrize("texte", ["", "pas de JSON ici", "[1, 2]", '{"nom": 5, "experiences": "x"}'])
def test_une_reponse_illisible_leve_une_erreur(texte):
    with pytest.raises(CvIllisible):
        lire_reponse(texte)


# --- Route /api/cv -------------------------------------------------------------------------------------------------------

def test_la_route_rend_le_cv_et_passe_le_pdf_a_claude(claude):
    reponse = post({"poste": "Comptable", "fichier": {"nom": "cv.pdf", "type": "application/pdf", "donnees": b64(PDF)}},
                   "203.0.113.101")
    assert reponse.status_code == 200 and reponse.headers["Cache-Control"] == "no-store"
    assert reponse.get_json()["cv"]["nom"] == "Awa Ndiaye"
    appel = claude.appels[-1]
    assert appel["system"] == CONSIGNE_CV and appel["attachment"]["type"] == "document"


def test_sans_jeton_csrf_la_route_refuse():
    assert post({"parcours": "BTS comptabilité en 2023, stage."}, "203.0.113.102", csrf=False).status_code == 403


def test_un_fichier_refuse_ou_une_demande_vide_donne_400(claude):
    assert post({"poste": "Comptable"}, "203.0.113.103").status_code == 400
    mauvais = {"fichier": {"nom": "x.html", "type": "text/html", "donnees": b64(b"<p>")}}
    assert post(mauvais, "203.0.113.104").status_code == 400
    assert claude.appels == []


def test_une_reponse_illisible_de_l_ia_donne_502(claude):
    claude.reponse["texte"] = "Désolé, je ne peux pas."
    reponse = post({"parcours": "BTS comptabilité en 2023, stage."}, "203.0.113.105")
    assert reponse.status_code == 502 and "réessaie" in reponse.get_json()["error"].lower()


def test_sans_claude_le_site_le_dit(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reponse = post({"parcours": "BTS comptabilité en 2023, stage."}, "203.0.113.106")
    assert reponse.status_code == 503


def test_le_contenu_du_cv_n_est_jamais_ecrit_dans_les_journaux(claude, caplog):
    caplog.set_level("DEBUG")
    post({"parcours": "Récit très personnel de Fatou, téléphone 77 000 00 00."}, "203.0.113.107")
    assert "Fatou" not in caplog.text and "77 000" not in caplog.text


def test_la_route_est_limitee_et_une_requete_longue():
    assert "cv" in app_module.GUARDED_LIMITS and "/api/cv" in LONG_PATHS
    # Le plafond d'IA n'est pas pris par rate_guard (avant toute vérification) : la route le prend elle-même.
    assert "cv" not in app_module.AI_BUDGET_BUCKETS


def test_seule_une_demande_valide_consomme_le_plafond_ia(claude, monkeypatch):
    """Relecture Codex de #606 (P1) : une demande vide ou refusée, même avec un jeton CSRF valide, ne doit pas user le
    plafond d'IA du jour, partagé par le chat, le planificateur et la voix."""
    prises = []
    monkeypatch.setattr(app_module.AI_BUDGET, "take", lambda: prises.append(1) or True)
    assert post({"poste": "Comptable"}, "203.0.113.111").status_code == 400
    mauvais = {"fichier": {"nom": "x.html", "type": "text/html", "donnees": b64(b"<p>")}}
    assert post(mauvais, "203.0.113.112").status_code == 400
    assert prises == [] and claude.appels == []
    assert post({"parcours": "BTS comptabilité en 2023, stage."}, "203.0.113.113").status_code == 200
    assert prises == [1]


def test_plafond_ia_atteint_le_cv_n_est_pas_cree(claude, monkeypatch):
    monkeypatch.setattr(app_module.AI_BUDGET, "take", lambda: False)
    reponse = post({"parcours": "BTS comptabilité en 2023, stage."}, "203.0.113.114")
    assert reponse.status_code == 503 and claude.appels == []


# --- Modèles (« Trois modèles c'est très court », propriétaire, 15 novembre 2026) --------------------------------------

MODELES = ("sobre", "moderne", "teranga", "classique", "minimal", "creatif", "ocean", "baobab", "elegant")


def test_neuf_modeles_proposes_chacun_avec_son_style():
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    js = (app_module.BASE_DIR / "static" / "cv.js").read_text(encoding="utf-8")
    css = (app_module.BASE_DIR / "static" / "site.css").read_text(encoding="utf-8")
    for nom in MODELES:
        assert f'data-modele="{nom}"' in html, nom
        assert f"'{nom}'" in js, nom  # accepté par la page (et retrouvé après rechargement)
        assert f".cv-feuille.{nom} " in css, nom  # un style propre


def test_l_iphone_ne_transforme_pas_le_telephone_et_l_e_mail_en_liens():
    # Capture du propriétaire (15 novembre 2026) : Safari soulignait le numéro et l'e-mail du CV comme des liens.
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    assert '<meta name="format-detection" content="telephone=no,email=no,address=no">' in html


def test_mon_cv_est_dans_le_plan_du_site_avec_les_mots_que_les_jeunes_cherchent():
    # 17 novembre 2026 : /cv manquait au plan du site envoyé à Google, et son titre (« Mon CV · Teranga AI ») ne
    # contenait ni « gratuit » ni « Sénégal ». Les règles communes des pages du plan (titre, description, canonique,
    # aperçu de partage, JSON-LD) sont vérifiées par tests/test_seo_quality.py.
    client = app_module.app.test_client()
    plan = client.get("/sitemap.xml", base_url="https://teranga-ai.fr").get_data(as_text=True)
    assert "<loc>https://teranga-ai.fr/cv</loc>" in plan
    page = client.get("/cv", base_url="https://teranga-ai.fr").get_data(as_text=True)
    titre = page.split("<title>", 1)[1].split("</title>", 1)[0]
    assert "CV" in titre and "gratuit" in titre and "Sénégal" in titre
    assert 'property="og:title"' in page and '"@type": "WebApplication"' in page


def test_la_licence_des_icones_lucide_est_livree_avec_le_site():
    from pathlib import Path

    racine = Path(__file__).resolve().parents[1]
    licence = (racine / "static" / "LICENCE-lucide.txt").read_text(encoding="utf-8")
    assert "ISC License" in licence and "Lucide Icons and Contributors" in licence
    assert "Lucide" in (racine / "static" / "cv.js").read_text(encoding="utf-8")


def test_le_cv_pret_propose_de_l_envoyer_a_un_ami_sur_whatsapp_sans_les_donnees_du_cv():
    """Bouche-à-oreille : le message partagé ne contient que l'adresse de /cv (marquée ?ref=wa pour compter les arrivées)."""
    from urllib.parse import parse_qs, unquote, urlparse

    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    resultat = html[html.index('id="cvResultat"'):]
    lien = re.search(r'<a [^>]*id="cvPartager"[^>]*>', resultat)
    assert lien, "le bouton de partage doit être dans la section « Ton CV est prêt »"
    balise = lien.group(0)
    href = re.search(r'href="([^"]+)"', balise).group(1).replace("&amp;", "&")
    adresse = urlparse(href)
    assert (adresse.scheme, adresse.netloc) == ("https", "wa.me")
    texte = unquote(parse_qs(adresse.query)["text"][0])
    assert texte.endswith("https://teranga-ai.fr/cv?ref=wa") and "gratuit" in texte
    assert 'target="_blank"' in balise and 'rel="noopener noreferrer"' in balise
    assert "Envoyer à un ami sur WhatsApp" in resultat[lien.end():lien.end() + 80]


def test_un_exemple_fictif_montre_le_cv_fini_avant_le_formulaire():
    """Montrer le résultat avant de demander quoi que ce soit : un CV fini, d'une personne fictive dite comme telle,
    et un bouton qui mène au formulaire. L'exemple est dessiné par cv.js (même rendu que le vrai CV)."""
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    debut = html.index('id="cvExemple"')
    assert debut < html.index('id="cvForm"')
    exemple = html[debut:html.index("</section>", debut)]
    assert "personne fictive" in exemple
    assert 'id="cvExempleFeuille"' in exemple
    assert re.search(r'<a [^>]*href="#cvForm"[^>]*>Faire le mien</a>', exemple)


def test_chaque_creation_de_cv_laisse_une_ligne_de_latence_sans_donnee_du_cv(claude, monkeypatch):
    """Combien de temps attend la personne ? Une ligne « latence route=cv » par demande (services/latency.py) :
    des nombres et des étiquettes fixes, jamais le parcours, le poste ni le CV."""
    import latence_harness as h

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")  # le banc de latence retire la clé quand il est importé
    handler = h.capture_lines()
    try:
        for corps, ip, code in (({"parcours": "BTS comptabilité en 2023, deux stages.", "poste": "Comptable"}, "203.0.113.90", 200),
                                ({"parcours": ""}, "203.0.113.91", 400)):
            reponse = post(corps, ip)
            assert reponse.status_code == code
            reponse.get_data()
            reponse.close()  # la ligne part à la fermeture de la réponse, comme pour le chat
    finally:
        h.release_lines(handler)
    assert len(handler.lines) == 2, handler.lines
    ok, invalide = (h.fields(ligne) for ligne in handler.lines)
    assert ok["route"] == "cv" and ok["statut"] == "ok" and ok["modele"] != "-"
    assert float(ok["total_ms"]) >= float(ok["fournisseur_ms"]) >= 0
    assert invalide["route"] == "cv" and invalide["statut"] == "invalide" and invalide["fournisseur_ms"] == "-"
    texte = "".join(handler.lines)
    assert "Comptable" not in texte and "BTS" not in texte and "Awa" not in texte


def test_la_page_repond_aux_questions_que_les_gens_tapent_sur_google():
    """Recherches vues dans la campagne Google Ads CV (22 novembre 2026) : « comment faire un cv », « exemple de cv pour
    demande d'emploi ». Les réponses ne disent que ce que fait la page et les règles du skill cv-senegal."""
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    debut = html.index('id="cvFaqTitre"')
    faq = html[debut:html.index("</section>", debut)]
    for question in ("Comment faire un CV pour une demande d’emploi ?", "Je n’ai pas d’expérience : que mettre dans mon CV ?",
                     "Quel modèle de CV choisir ?", "C’est gratuit ? Mon CV est-il gardé ?", "Où envoyer mon CV ensuite ?"):
        assert f"<h3>{question}</h3>" in faq, question
    assert 'href="/offres-emploi"' in faq and "Teranga ne les garde pas" in faq
    donnees = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    (faq_ld,) = [n for n in donnees["@graph"] if n["@type"] == "FAQPage"]
    assert len(faq_ld["mainEntity"]) == 5
    assert all("<" not in q["acceptedAnswer"]["text"] for q in faq_ld["mainEntity"])  # texte seul, sans balise


def test_le_depart_sans_cv_est_propose_d_abord_sans_fichier_a_chercher():
    """« Go 1 » du 23 novembre 2026 : les visiteurs venus de la pub (« comment faire un cv ») n'ont souvent pas de CV
    sur leur téléphone. Le départ par défaut est donc le récit du parcours, avec le nom à part ; le fichier reste au
    choix."""
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    choix = html[html.index('<fieldset class="cv-choix">'):html.index("</fieldset>")]
    assert choix.index('value="parcours"') < choix.index('value="fichier"')
    assert re.search(r'<input type="radio" name="depart" value="parcours" checked>', choix)
    assert "pas besoin de fichier" in choix
    assert re.search(r'<div class="cv-champ" id="cvBlocFichier" hidden>', html)
    assert re.search(r'<div class="cv-bloc-parcours" id="cvBlocParcours">', html)
    nom = re.search(r'<input id="cvNom"[^>]*>', html)
    assert nom and 'autocomplete="name"' in nom.group(0) and 'maxlength="80"' in nom.group(0)


def test_un_recit_au_maximum_avec_un_nom_reste_accepte_par_le_serveur():
    """Relecture Codex (#645) : le nom part en tête du parcours (« Nom : …\\n ») ; un récit à la longueur maximale du
    champ, avec le nom le plus long, ne doit pas dépasser la limite du serveur (sinon 400, alors que le formulaire
    l'acceptait)."""
    html = app_module.app.test_client().get("/cv", base_url=B).get_data(as_text=True)
    recit_max = int(re.search(r'<textarea id="cvParcours"[^>]*maxlength="(\d+)"', html).group(1))
    nom_max = int(re.search(r'<input id="cvNom"[^>]*maxlength="(\d+)"', html).group(1))
    parcours = "Nom : " + "n" * nom_max + "\n" + "r" * recit_max
    construire_demande({"parcours": parcours, "poste": "Comptable"})  # ne lève rien
