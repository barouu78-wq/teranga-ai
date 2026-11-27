"""Préchargement privé de Chrome depuis les résultats de Google (/.well-known/traffic-advice).

Les journaux de novembre 2026 montraient « GET /.well-known/traffic-advice » en 404 (agent « Chrome Privacy
Preserving Prefetch Proxy ») : sans ce fichier, Chrome ne charge pas teranga-ai.fr à l'avance depuis les résultats
de recherche.

Les compteurs de visites ne changent pas : une page préchargée puis ouverte n'envoie pas de second GET, l'ignorer
ferait donc perdre de vraies visites (relecture Codex de la PR #680). Et Google ne précharge que ses propres
résultats, qui ne portent ni les marques utm_source des réseaux ni celles du widget.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_traffic_advice_autorise_le_prechargement_par_google():
    from app import app

    reponse = app.test_client().get("/.well-known/traffic-advice", base_url="https://teranga-ai.fr")
    assert reponse.status_code == 200
    # Type exigé par Chrome : un autre type (application/json) fait ignorer le fichier.
    assert reponse.mimetype == "application/trafficadvice+json"
    assert reponse.get_json() == [{"user_agent": "prefetch-proxy", "fraction": 1.0}]
    assert "max-age" in reponse.headers.get("Cache-Control", "")
