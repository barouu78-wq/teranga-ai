"""Un JSON très imbriqué reçoit une erreur 400, pas une erreur 500 (RecursionError)."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402

B = "https://teranga-ai.fr"


def _client(ip):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    return client, {"X-CSRF-Token": token, "Origin": B, "Content-Type": "application/json"}, {"REMOTE_ADDR": ip}


def test_deeply_nested_json_is_refused_with_400_on_every_json_route():
    client, headers, env = _client("203.0.113.180")
    body = "[" * 200000
    for path in ("/chat", "/tts", "/api/report", "/api/projects/plan"):
        response = client.post(path, data=body, base_url=B, headers=headers, environ_base=env)
        assert response.status_code == 400, (path, response.status_code)
        assert response.get_json() == {"error": "Requête invalide."}, path


def test_normal_json_and_invalid_json_keep_their_behaviour():
    client, headers, env = _client("203.0.113.181")
    ok = client.post("/api/report", json={"reply": "Une réponse à signaler", "reason": "inappropriate"},
                     base_url=B, headers=headers, environ_base=env)
    assert ok.status_code == 200 and ok.get_json() == {"ok": True}
    broken = client.post("/api/report", data="{pas du json", base_url=B, headers=headers, environ_base=env)
    assert broken.status_code == 400
