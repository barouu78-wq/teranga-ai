"""Préchargement privé de Chrome depuis les résultats de Google (/.well-known/traffic-advice).

Les journaux de novembre 2026 montraient « GET /.well-known/traffic-advice » en 404 (agent « Chrome Privacy
Preserving Prefetch Proxy ») : sans ce fichier, Chrome ne charge pas teranga-ai.fr à l'avance depuis les résultats
de recherche. Une page préchargée n'a encore été vue par personne : elle ne compte pas comme une visite.
"""

import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key")

B = "https://teranga-ai.fr"
CLE = "un-mot-de-passe-solide-456"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"


def _client():
    from app import app

    return app.test_client()


def _compte(client, reseau, ip):
    page = client.post("/stats-partenaires", data={"cle": CLE}, base_url=B,
                       environ_base={"REMOTE_ADDR": ip}).get_data(as_text=True)
    trouve = re.search(rf"<td>Visites venues des réseaux</td><td>{reseau}</td><td>(\d+)</td>", page)
    return int(trouve.group(1)) if trouve else 0


def test_traffic_advice_autorise_le_prechargement_par_google():
    reponse = _client().get("/.well-known/traffic-advice", base_url=B)
    assert reponse.status_code == 200
    # Type exigé par Chrome : un autre type (application/json) fait ignorer le fichier.
    assert reponse.mimetype == "application/trafficadvice+json"
    assert reponse.get_json() == [{"user_agent": "prefetch-proxy", "fraction": 1.0}]
    assert "max-age" in reponse.headers.get("Cache-Control", "")


def test_une_page_prechargee_n_est_pas_comptee_comme_visite(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()
    avant = _compte(client, "youtube", "203.0.113.91")
    for entete in ({"Sec-Purpose": "prefetch"}, {"Sec-Purpose": "prefetch;anonymous-client-ip"}, {"Purpose": "prefetch"}):
        reponse = client.get("/?utm_source=youtube", base_url=B, headers={"User-Agent": IPHONE, **entete},
                             environ_base={"REMOTE_ADDR": "203.0.113.92"})
        assert reponse.status_code == 200  # la page est bien servie, elle n'est juste pas comptée
    assert _compte(client, "youtube", "203.0.113.91") == avant
    # La même visite, ouverte pour de vrai, compte toujours.
    client.get("/?utm_source=youtube", base_url=B, headers={"User-Agent": IPHONE}, environ_base={"REMOTE_ADDR": "203.0.113.93"})
    assert _compte(client, "youtube", "203.0.113.91") == avant + 1


def test_un_clic_sur_le_widget_precharge_n_est_pas_compte(monkeypatch):
    monkeypatch.setenv("STATS_TOKEN", CLE)
    client = _client()

    def lignes_widget():
        page = client.post("/stats-partenaires", data={"cle": CLE}, base_url=B,
                           environ_base={"REMOTE_ADDR": "203.0.113.94"}).get_data(as_text=True)
        return page.count("hotel-precharge-test")

    avant = lignes_widget()
    client.get("/?utm_source=hotel-precharge-test&utm_medium=widget", base_url=B,
               headers={"User-Agent": IPHONE, "Sec-Purpose": "prefetch"}, environ_base={"REMOTE_ADDR": "203.0.113.95"})
    assert lignes_widget() == avant
