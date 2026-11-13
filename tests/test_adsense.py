"""Annonces Google AdSense : éteintes par défaut, une seule annonce en bas des pages de guide.

Demande du propriétaire (13 novembre 2026) : « rajouter de la publicité » qui rapporte. Maquette validée : une annonce
marquée « Publicité » en fin de page de guide, jamais au milieu du texte, jamais sur l'accueil (chat), les urgences
ni la confidentialité. Google ne prend en charge qu'une CSP « stricte » (nonce + 'strict-dynamic') : elle ne
s'applique qu'aux pages qui portent une annonce, et chacun de nos scripts y reçoit le nonce.
"""

import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services.adsense import adsense_config, inject_adsense  # noqa: E402

CLIENT = "ca-pub-1234567890123456"
SLOT = "9876543210"
GUIDES = ["/visiter-goree", "/lieux/goree", "/regions/thies", "/fr/senegal-visa", "/explorer",
          "/calendrier-fetes-senegal", "/lieux"]
SANS_PUB = ["/", "/urgences", "/confidentialite", "/privacy", "/trip-planner", "/offres-partenaires", "/partage",
            "/une-page-qui-n-existe-pas"]


@pytest.fixture
def ads(monkeypatch):
    monkeypatch.setitem(app_module.app.config, "ADSENSE", adsense_config(CLIENT, SLOT))


def get(path):
    return app_module.app.test_client().get(path, base_url="https://teranga-ai.fr")


@pytest.mark.parametrize(("client", "slot"), [
    ("", ""), ("", SLOT), ("pub-1234567890123456", SLOT), ("ca-pub-123", SLOT), (CLIENT, "abc"),
    (CLIENT + '"><script>', SLOT), (CLIENT, SLOT + '"'),
])
def test_sans_identifiants_valides_la_publicite_reste_eteinte(client, slot):
    assert adsense_config(client, slot) is None


def test_le_compte_seul_publie_ads_txt_sans_afficher_d_annonce(monkeypatch):
    """Étape de vérification du site par Google : ads.txt d'abord, les annonces une fois le bloc créé."""
    monkeypatch.setitem(app_module.app.config, "ADSENSE", adsense_config(CLIENT, ""))
    assert get("/ads.txt").status_code == 200
    response = get("/visiter-goree")
    assert "adsbygoogle" not in response.get_data(as_text=True)
    assert "strict-dynamic" not in response.headers["Content-Security-Policy"]


def test_eteinte_par_defaut_rien_ne_change(monkeypatch):
    monkeypatch.setitem(app_module.app.config, "ADSENSE", None)
    response = get("/visiter-goree")
    assert "adsbygoogle" not in response.get_data(as_text=True)
    assert "strict-dynamic" not in response.headers["Content-Security-Policy"]
    assert get("/ads.txt").status_code == 404
    assert "AdSense" not in get("/confidentialite").get_data(as_text=True)


def test_ads_txt_declare_le_compte_google(ads):
    response = get("/ads.txt")
    assert response.status_code == 200 and response.mimetype == "text/plain"
    assert response.get_data(as_text=True).strip() == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"


@pytest.mark.parametrize("path", GUIDES)
def test_une_seule_annonce_marquee_publicite_en_fin_de_page(ads, path):
    response = get(path)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert body.count('class="adsbygoogle"') == 1
    assert body.count(f"/pagead/js/adsbygoogle.js?client={CLIENT}") == 1
    assert f'data-ad-client="{CLIENT}"' in body and f'data-ad-slot="{SLOT}"' in body
    slot = body.index('class="ad-slot"')
    assert ">Publicité<" in body[slot:slot + 200]
    # Après tout le contenu de la page : plus rien entre l'annonce et la fin de l'article ou de <main>. Dans la
    # carte de l'article quand elle ferme la page (comme sur la maquette), même suivie d'un retour à la ligne.
    end = body.index("</aside>", slot) + len("</aside>")
    assert re.match(r"(</article>)?\s*</main>", body[end:]), body[end:end + 80]
    assert body[end:].startswith("</article>") == (path != "/explorer")
    assert slot > body.index("<h1")


@pytest.mark.parametrize("path", GUIDES)
def test_la_csp_stricte_de_google_couvre_tous_nos_scripts(ads, path):
    response = get(path)
    body = response.get_data(as_text=True)
    csp = response.headers["Content-Security-Policy"]
    script_src = csp.split("script-src", 1)[1].split(";", 1)[0]
    nonce = re.search(r"'nonce-([^']+)'", script_src).group(1)
    assert "'strict-dynamic'" in script_src and "'unsafe-inline'" not in script_src
    assert "frame-src https:" in csp and "object-src 'none'" in csp
    for tag in re.findall(r"<script\b[^>]*>", body, re.IGNORECASE):
        if "application/ld+json" not in tag:
            assert f'nonce="{nonce}"' in tag, tag
    # Le nonce change à chaque visite : la page n'est plus gardée en cache public.
    assert "public" not in response.headers["Cache-Control"]


def test_aucune_page_avec_annonce_ne_garde_de_script_dans_un_attribut(ads):
    """Relecture Gitar de #598 : la CSP stricte bloque onsubmit=, onclick=… et les liens « javascript: ». Sur /lieux,
    Entrée rechargeait la page. Toutes les pages du plan du site qui portent une annonce sont vérifiées."""
    sitemap = get("/sitemap.xml").get_data(as_text=True)
    paths = {"/explorer", "/lieux"} | set(re.findall(r"<loc>https://teranga-ai\.fr([^<]*)</loc>", sitemap))
    with_ad = 0
    for path in sorted(paths):
        body = get(path).get_data(as_text=True)
        if 'class="adsbygoogle"' not in body:
            continue
        with_ad += 1
        assert not re.search(r"\son[a-z]+\s*=", body, re.IGNORECASE), path
        assert "javascript:" not in body.lower(), path
    assert with_ad > 100


@pytest.mark.parametrize("path", SANS_PUB)
def test_jamais_de_pub_sur_l_accueil_les_urgences_ni_la_confidentialite(ads, path):
    response = get(path)
    assert "adsbygoogle" not in response.get_data(as_text=True)
    assert "strict-dynamic" not in response.headers.get("Content-Security-Policy", "")


def test_jamais_de_pub_sur_les_pages_privees(ads):
    response = get("/stats-partenaires")
    assert "adsbygoogle" not in response.get_data(as_text=True)


def test_un_script_inconnu_ne_recoit_jamais_le_nonce():
    """Sur une page déjà protégée par un nonce, seul le script du site (/static/) le reçoit : un script glissé dans
    le contenu reste bloqué, comme avant."""
    from flask import Response

    html = ('<!doctype html><html lang="fr"><head><script src="/static/theme.js"></script></head><body><main>'
            '<article><h1>Gorée</h1><script>alert(1)</script><script src="https://exemple.invalid/x.js"></script>'
            '</article></main><footer class="site-footer"></footer></body></html>')
    response, nonce = inject_adsense(Response(html, mimetype="text/html"), adsense_config(CLIENT, SLOT),
                                     path="/lieux/goree", nonce="abc")
    body = response.get_data(as_text=True)
    assert nonce == "abc"
    assert '<script src="/static/theme.js" nonce="abc">' in body
    assert "<script>alert(1)</script>" in body
    assert '<script src="https://exemple.invalid/x.js">' in body


def test_l_etiquette_suit_la_langue_de_la_page(ads):
    body = get("/privacy").get_data(as_text=True)
    assert "adsbygoogle" not in body
    from flask import Response

    html = ('<!doctype html><html lang="en"><head></head><body><main><article><h1>Senegal</h1></article></main>'
            '<footer class="site-footer"></footer></body></html>')
    response, _ = inject_adsense(Response(html, mimetype="text/html"), adsense_config(CLIENT, SLOT),
                                 path="/en/senegal-travel-guide")
    assert ">Advertisement<" in response.get_data(as_text=True)


def test_la_confidentialite_explique_la_publicite_quand_elle_est_allumee(ads):
    for path, mots in (("/confidentialite", ("Publicité", "Google AdSense", "consentement")),
                       ("/privacy", ("Advertising", "Google AdSense", "consent"))):
        body = get(path).get_data(as_text=True)
        for mot in mots:
            assert mot in body, (path, mot)
        assert "https://policies.google.com/technologies/partner-sites" in body
