"""V5 « faire venir les gens » : les liens marqués des publications (?utm_source=tiktok…) disent d'où viennent les
visiteurs, sans outil de suivi extérieur ni donnée personnelle (Go V5 du propriétaire, 6 novembre 2026).

Seuls les réseaux connus sont comptés (une valeur inventée ne crée pas de ligne), les aperçus de liens des robots
ne comptent pas, et un script ne peut pas gonfler les chiffres. Les chiffres sont sur /stats-partenaires.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

B = "https://teranga-ai.fr"
CLE = "un-mot-de-passe-solide-123"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"


def _client():
    from app import app

    return app.test_client()


def _stats(client, ip):
    return client.post("/stats-partenaires", data={"cle": CLE}, base_url=B,
                       environ_base={"REMOTE_ADDR": ip}).get_data(as_text=True)


def _compte(page, reseau):
    """Visites comptées pour ce réseau ce mois-ci (0 sans ligne) : le compteur est partagé par toute la suite."""
    trouve = re.search(rf"<td>Visites venues des réseaux</td><td>{reseau}</td><td>(\d+)</td>", page)
    return int(trouve.group(1)) if trouve else 0


def _visite(client, chemin, ip, agent=IPHONE):
    return client.get(chemin, base_url=B, headers={"User-Agent": agent}, environ_base={"REMOTE_ADDR": ip})


def test_les_visites_venues_d_un_reseau_sont_comptees_par_reseau(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _stats(client, "203.0.113.83")
    assert _visite(client, "/?utm_source=tiktok", "203.0.113.81").status_code == 200
    assert _visite(client, "/joj-dakar-2026?utm_source=tiktok&utm_campaign=s45", "203.0.113.82").status_code == 200
    assert _visite(client, "/?utm_source=WhatsApp", "203.0.113.83").status_code == 200
    apres = _stats(client, "203.0.113.83")
    assert _compte(apres, "tiktok") - _compte(avant, "tiktok") == 2
    assert _compte(apres, "whatsapp") - _compte(avant, "whatsapp") == 1


def test_un_reseau_inconnu_ou_une_visite_sans_lien_marque_ne_compte_pas(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    _visite(client, "/?utm_source=reseau-invente-x", "203.0.113.84")
    _visite(client, "/?utm_source=%3Cscript%3E", "203.0.113.84")
    _visite(client, "/", "203.0.113.84")
    page = _stats(client, "203.0.113.84")
    assert "reseau-invente-x" not in page
    assert "&lt;script" not in page and "<script>" not in page.split("<main>")[-1]


def test_les_apercus_de_liens_des_robots_ne_comptent_pas(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    # Aperçu de lien (Facebook, Instagram) ou robot : pas un visiteur. Aucun autre test ne compte « instagram ».
    _visite(client, "/?utm_source=instagram", "203.0.113.85", agent="facebookexternalhit/1.1")
    _visite(client, "/?utm_source=instagram", "203.0.113.85", agent="")
    assert _compte(_stats(client, "203.0.113.85"), "instagram") == 0


def test_l_apercu_de_lien_de_whatsapp_ne_compte_pas(monkeypatch):
    """Relectures Codex et Gitar de #577 : WhatsApp fabrique l'aperçu avec l'agent « WhatsApp/2.x », sans « bot »."""
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _compte(_stats(client, "203.0.113.87"), "whatsapp")
    _visite(client, "/?utm_source=whatsapp", "203.0.113.87", agent="WhatsApp/2.23.20.0 A")
    _visite(client, "/?utm_source=whatsapp", "203.0.113.87", agent="WhatsApp/2.24.8.78 i")
    assert _compte(_stats(client, "203.0.113.87"), "whatsapp") == avant
    _visite(client, "/?utm_source=whatsapp", "203.0.113.88")  # la vraie visite, dans le navigateur du téléphone
    assert _compte(_stats(client, "203.0.113.88"), "whatsapp") == avant + 1


def test_la_colonne_des_chiffres_ne_dit_plus_clics(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    _visite(client, "/?utm_source=facebook", "203.0.113.89")
    page = _stats(client, "203.0.113.89")
    assert "<th>Lien</th><th>Origine</th><th>Nombre</th>" in page
    assert "<th>Clics</th>" not in page


def test_un_script_ne_peut_pas_gonfler_les_visites(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _compte(_stats(client, "203.0.113.86"), "youtube")
    for _ in range(10):
        assert _visite(client, "/?utm_source=youtube", "203.0.113.86").status_code == 200
    assert _compte(_stats(client, "203.0.113.86"), "youtube") - avant == 6


def test_les_liens_a_utiliser_sont_ecrits_pour_le_proprietaire():
    texte = open(os.path.join(os.path.dirname(__file__), "..", "docs", "LIENS-MARQUES.md"), encoding="utf-8").read()
    for reseau in ("tiktok", "instagram", "whatsapp", "facebook", "youtube"):
        assert f"https://teranga-ai.fr/?utm_source={reseau}" in texte


def test_seul_un_vrai_navigateur_compte(monkeypatch):
    """Mesure du 6 novembre : à 12 h 52 UTC, trois visites dans la même seconde (une par lien marqué), agent
    « Mozilla/5.0 (compatible) » : un outil automatique, compté à tort. Seuls Safari, Chrome, Firefox et les
    navigateurs intégrés des applications (TikTok, Instagram…, tous WebKit ou Gecko) comptent désormais."""
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _compte(_stats(client, "203.0.113.90"), "tiktok")
    _visite(client, "/?utm_source=tiktok", "203.0.113.90", agent="Mozilla/5.0 (compatible)")
    _visite(client, "/?utm_source=tiktok", "203.0.113.90", agent="Mozilla/5.0")
    _visite(client, "/?utm_source=tiktok", "203.0.113.90", agent="okhttp/4.12.0")
    assert _compte(_stats(client, "203.0.113.90"), "tiktok") == avant
    navigateurs = [
        # Navigateur intégré de TikTok sur iPhone, Chrome sur Android, Firefox sur ordinateur.
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 musical_ly_37.0.0",
        "Mozilla/5.0 (Linux; Android 14; SM-A145F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0",
    ]
    for n, agent in enumerate(navigateurs):
        _visite(client, "/?utm_source=tiktok", f"203.0.113.{91 + n}", agent=agent)
    assert _compte(_stats(client, "203.0.113.93"), "tiktok") == avant + 3
