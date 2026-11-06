"""V5 « faire venir les gens » : les liens marqués des publications (?utm_source=tiktok…) disent d'où viennent les
visiteurs, sans outil de suivi extérieur ni donnée personnelle (Go V5 du propriétaire, 6 novembre 2026).

Seuls les réseaux connus sont comptés (une valeur inventée ne crée pas de ligne), les aperçus de liens des robots
ne comptent pas, et un script ne peut pas gonfler les chiffres. Les chiffres sont sur /stats-partenaires.
"""

import os

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


def _visite(client, chemin, ip, agent=IPHONE):
    return client.get(chemin, base_url=B, headers={"User-Agent": agent}, environ_base={"REMOTE_ADDR": ip})


def test_les_visites_venues_d_un_reseau_sont_comptees_par_reseau(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    assert _visite(client, "/?utm_source=tiktok", "203.0.113.81").status_code == 200
    assert _visite(client, "/joj-dakar-2026?utm_source=tiktok&utm_campaign=s45", "203.0.113.82").status_code == 200
    assert _visite(client, "/?utm_source=WhatsApp", "203.0.113.83").status_code == 200
    page = _stats(client, "203.0.113.83")
    assert "<td>Visites venues des réseaux</td><td>tiktok</td><td>2</td>" in page
    assert "<td>Visites venues des réseaux</td><td>whatsapp</td><td>1</td>" in page


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
    # Aperçu de lien (WhatsApp, Facebook) ou robot : pas un visiteur.
    _visite(client, "/?utm_source=instagram", "203.0.113.85", agent="facebookexternalhit/1.1")
    _visite(client, "/?utm_source=instagram", "203.0.113.85", agent="")
    assert "<td>instagram</td>" not in _stats(client, "203.0.113.85")


def test_un_script_ne_peut_pas_gonfler_les_visites(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    for _ in range(10):
        assert _visite(client, "/?utm_source=youtube", "203.0.113.86").status_code == 200
    assert "<td>youtube</td><td>6</td>" in _stats(client, "203.0.113.86")


def test_les_liens_a_utiliser_sont_ecrits_pour_le_proprietaire():
    texte = open(os.path.join(os.path.dirname(__file__), "..", "docs", "LIENS-MARQUES.md"), encoding="utf-8").read()
    for reseau in ("tiktok", "instagram", "whatsapp", "facebook", "youtube"):
        assert f"https://teranga-ai.fr/?utm_source={reseau}" in texte
