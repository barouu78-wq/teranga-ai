"""Mon CV : compter où les visiteurs s'arrêtent (« Go 1 » du propriétaire, 23 novembre 2026).

Le 22 novembre, 8 visiteurs venus de la pub ont ouvert /cv et aucun n'a envoyé de CV, sans qu'on sache à quelle étape
ils s'arrêtent. Chaque étape du formulaire (bouton « Faire le mien », premier champ touché, envoi refusé faute de CV ou
de parcours, envoi) est comptée par mois, comme les visites venues des réseaux : rien de ce que la personne écrit,
ni adresse IP, ni identifiant. Seuls les vrais navigateurs comptent, et un script ne peut pas gonfler les chiffres.
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


_IP_STATS = iter(range(170, 250))


def _comptes(client):
    """Étapes comptées ce mois-ci. La page privée n'accepte que 5 essais de mot de passe par minute et par visiteur :
    chaque lecture vient d'une adresse différente."""
    page = client.post("/stats-partenaires", data={"cle": CLE}, base_url=B,
                       environ_base={"REMOTE_ADDR": f"203.0.113.{next(_IP_STATS)}"}).get_data(as_text=True)
    assert "Mot de passe" not in page and "Trop d'essais" not in page
    return {e: int(n) for e, n in re.findall(r"<td>Étapes du formulaire Mon CV</td><td>([a-z-]+)</td><td>(\d+)</td>", page)}


def _compte(client, etape):
    return _comptes(client).get(etape, 0)


def _etape(client, nom, ip, agent=IPHONE):
    return client.get(f"/cv/etape/{nom}", base_url=B, headers={"User-Agent": agent}, environ_base={"REMOTE_ADDR": ip})


def test_chaque_etape_connue_est_comptee_sans_rien_renvoyer(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    etapes = ("faire-le-mien", "debut", "refus-fichier", "refus-parcours", "envoi")
    avant = _comptes(client)
    for i, etape in enumerate(etapes):
        reponse = _etape(client, etape, f"203.0.113.{141 + i}")
        assert reponse.status_code == 204 and reponse.data == b""
        assert reponse.headers["Cache-Control"] == "no-store"
    apres = _comptes(client)
    for etape in etapes:
        assert apres.get(etape, 0) - avant.get(etape, 0) == 1, etape


def test_une_etape_inconnue_n_existe_pas(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    assert _etape(client, "inventee", "203.0.113.150").status_code == 404
    assert _compte(client, "inventee") == 0


def test_les_robots_ne_comptent_pas(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _compte(client, "debut")
    for i, agent in enumerate(("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "curl/8.0", "")):
        assert _etape(client, "debut", f"203.0.113.{151 + i}", agent).status_code == 204
    assert _compte(client, "debut") == avant


def test_un_script_ne_peut_pas_gonfler_les_etapes(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _compte(client, "envoi")
    for _ in range(10):
        _etape(client, "envoi", "203.0.113.160")
    assert _compte(client, "envoi") - avant == 6  # limite « visit_count » : 6 par minute et par visiteur


def test_la_confidentialite_le_dit():
    html = _client().get("/confidentialite", base_url=B).get_data(as_text=True)
    assert "étapes du formulaire « Mon CV »" in html and "sans enregistrer ce que vous écrivez" in html
