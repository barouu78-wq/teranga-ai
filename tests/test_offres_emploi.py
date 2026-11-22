"""Offres d'emploi (/offres-emploi) : décision du propriétaire du 22 novembre 2026, « on met juste leur lien ».

La page ne recopie aucune offre : elle renvoie vers la page d'offres de sites sénégalais vérifiés à la main (skill
offres-emploi : afficher peu, renvoyer toujours). Ces sites ne sont pas partenaires de Teranga ; Emploi Dakar interdit
les liens profonds dans ses conditions d'utilisation, on ne donne donc que sa page d'accueil.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.offres_emploi import SITES_EMPLOI  # noqa: E402

B = "https://teranga-ai.fr"


def page(chemin):
    reponse = app_module.app.test_client().get(chemin, base_url=B)
    return reponse.status_code, reponse.get_data(as_text=True)


def test_la_page_renvoie_vers_chaque_site_sans_recopier_d_offre():
    statut, html = page("/offres-emploi")
    assert statut == 200
    assert "<h1>Offres d’emploi au Sénégal</h1>" in html
    for site in SITES_EMPLOI:
        lien = re.search(rf'<a [^>]*href="{re.escape(site["url"])}"[^>]*>', html)
        assert lien, site["nom"]
        assert 'target="_blank"' in lien.group(0) and 'rel="noopener noreferrer"' in lien.group(0)
        assert site["nom"] in html
    assert "/go/" not in html  # pas des liens affiliés


def test_emploi_dakar_n_a_que_sa_page_d_accueil():
    # Conditions d'utilisation d'emploidakar.com (/conditions-generales-dutilisation-cgu/) : liens profonds interdits.
    (dakar,) = [s for s in SITES_EMPLOI if "emploidakar.com" in s["url"]]
    assert dakar["url"] == "https://www.emploidakar.com/"


def test_chaque_site_est_verifie_et_date():
    for site in SITES_EMPLOI:
        assert site["url"].startswith("https://"), site["nom"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", site["verifie_le"]), site["nom"]
        assert site["description"].endswith("."), site["nom"]


def test_la_page_dit_que_ce_ne_sont_pas_des_partenaires_et_met_en_garde():
    _, html = page("/offres-emploi")
    assert "ne sont pas partenaires de Teranga" in html
    assert "Ne paie jamais pour obtenir un emploi" in html
    assert "retiré sur simple demande" in html
    assert 'href="/cv"' in html
    assert "<script>" not in html  # aucun script dans la page (CSP)


def test_la_page_est_dans_le_plan_du_site():
    _, xml = page("/sitemap.xml")
    assert f"<loc>{B}/offres-emploi</loc>" in xml


def test_le_cv_pret_et_la_page_emploi_menent_aux_offres():
    _, html = page("/cv")
    assert 'href="/offres-emploi"' in html[html.index('id="cvResultat"'):]
    _, guide = page("/emploi-senegal")
    assert 'href="/offres-emploi"' in guide
