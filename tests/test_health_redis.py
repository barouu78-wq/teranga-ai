"""/health indique l'état de Redis pour vérifier REDIS_URL après un déploiement."""

import os

from flask import Flask

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def _app(redis_client, configured=None):
    from routes.system import register_system_routes

    app = Flask(__name__)
    register_system_routes(app, {
        "indexnow_key": "k", "issue_csrf": lambda *a: "t", "csrf_ttl": 60, "csrf_cookie": "c",
        "home_html": "<html></html>", "site_url": "https://teranga-ai.fr",
        "build_icon_png": lambda size: b"", "icon_svg": "<svg/>", "redis_client": redis_client,
        **({} if configured is None else {"redis_configured": configured}),
    })
    return app.test_client()


class _Redis:
    def __init__(self, fail=False):
        self.fail = fail

    def ping(self):
        if self.fail:
            raise ConnectionError("down")
        return True


def test_health_reports_redis_state_without_failing():
    assert _app(None).get("/health").get_json()["redis"] == "disabled"
    assert _app(_Redis()).get("/health").get_json()["redis"] == "ok"
    down = _app(_Redis(fail=True)).get("/health")
    assert down.status_code == 200 and down.get_json() == {"status": "ok", "service": "teranga-ai", "redis": "unavailable"}


def test_redis_client_has_short_timeouts():
    source = open(os.path.join(os.path.dirname(__file__), "..", "app.py"), encoding="utf-8").read()
    assert "socket_connect_timeout=2" in source and "socket_timeout=2" in source


def test_unreadable_redis_url_is_reported_as_misconfigured():
    assert _app(None, configured=True).get("/health").get_json()["redis"] == "misconfigured"
    assert _app(None, configured=False).get("/health").get_json()["redis"] == "disabled"
