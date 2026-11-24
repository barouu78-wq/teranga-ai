"""Un JSON très imbriqué (« [[[[… ») donne 400, jamais une erreur 500 (audit V3, P2-2).

`json.loads` lève RecursionError au-delà d'environ 1 000 niveaux, et `get_json(silent=True)` ne l'attrape pas.
`require_json_post` le gère déjà ; trois routes POST lisent leur JSON sans lui : partage, infos pratiques et
planificateur. Aucun appel réseau : le corps est refusé avant tout appel à l'IA.
"""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402

B = "https://teranga-ai.fr"
NESTED = "[" * 1500 + "]" * 1500


@pytest.mark.parametrize("path", ["/api/share/open", "/api/practical-info", "/api/trip-planner"])
def test_deeply_nested_json_is_a_bad_request_not_a_crash(path):
    response = app_module.app.test_client().post(
        path, data=NESTED, content_type="application/json",
        headers={"Origin": B}, base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.77"},
    )
    assert response.status_code in (400, 413), (path, response.status_code)
