"""Regression tests for the security/robustness audit fixes."""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest
from flask import Flask, jsonify

import app as app_module
from routes.explorer import register_explorer_routes
from services.explorer import render_explorer_page
from services.http_headers import add_security_headers
from services.identity import rate_limit_identity
from services.images import fetch_google_images, safe_image_fetch
from services.rate_limit import BoundedStore, allowed_request
import services.trip_planner as trip_planner


# --- Bounded in-memory state -------------------------------------------------

def test_bounded_store_evicts_least_recently_used_keys():
    store = BoundedStore(max_keys=3)
    for key in ("a", "b", "c"):
        store[key].append(1)
    store["a"]  # touch: "a" becomes most recent
    store["d"].append(1)
    assert list(store.keys()) == ["c", "a", "d"]


def test_bounded_store_without_factory_behaves_like_dict():
    store = BoundedStore(factory=None, max_keys=2)
    assert store.get("missing", 0) == 0
    store["x"] = 1.0
    assert store.pop("x", None) == 1.0
    with pytest.raises(KeyError):
        store["missing"]


def test_app_rate_limit_logs_are_bounded():
    for name in ("request_log", "image_request_log", "abuse_events", "abuse_blocks"):
        assert isinstance(getattr(app_module, name), BoundedStore)


# --- Redis TTL recovery ------------------------------------------------------

def test_redis_rate_limit_rearms_missing_ttl():
    class Redis:
        def __init__(self):
            self.count = 5  # key survived a crash between INCR and EXPIRE
            self.expired = []

        def incr(self, key):
            self.count += 1
            return self.count

        def ttl(self, key):
            return -1

        def expire(self, key, seconds):
            self.expired.append(seconds)

    redis = Redis()
    allowed_request(redis, None, "1.2.3.4", [], 10, 60, "chat")
    assert redis.expired == [60]


# --- Identity used for abuse keys -------------------------------------------

def test_rate_limit_identity_is_stable_without_cookie():
    assert rate_limit_identity("") == rate_limit_identity(None) == "anonymous"
    assert rate_limit_identity("bad cookie!") == "anonymous"
    valid = "A" * 24
    assert rate_limit_identity(valid) == valid


def test_abuse_key_is_stable_for_cookieless_requests():
    with app_module.app.test_request_context("/"):
        first = app_module.abuse_key("10.0.0.1")
    with app_module.app.test_request_context("/"):
        second = app_module.abuse_key("10.0.0.1")
    assert first == second


# --- Secret key --------------------------------------------------------------

def test_secret_key_is_not_plain_hash_of_openai_key():
    import hashlib

    api_key = os.environ["OPENAI_API_KEY"]
    if os.getenv("SECRET_KEY"):
        pytest.skip("SECRET_KEY configured in environment")
    assert app_module.app.config["SECRET_KEY"] != hashlib.sha256(api_key.encode()).hexdigest()
    assert len(app_module.app.config["SECRET_KEY"]) == 64


# --- Image proxy -------------------------------------------------------------

class _Upstream:
    def __init__(self, content_type, data=b"x"):
        self._type = content_type
        self._data = data
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n):
        return self._data[:n]


class _Opener:
    def __init__(self, upstream):
        self.upstream = upstream

    def open(self, req, timeout=None):
        return self.upstream


def test_safe_image_fetch_rejects_svg():
    opener = _Opener(_Upstream("image/svg+xml", b"<svg onload=alert(1)>"))
    with pytest.raises(ValueError):
        safe_image_fetch("https://upload.wikimedia.org/a.svg", 1000, opener=opener)


def test_safe_image_fetch_accepts_jpeg():
    opener = _Opener(_Upstream("image/jpeg", b"\xff\xd8data"))
    content_type, data = safe_image_fetch("https://upload.wikimedia.org/a.jpg", 1000, opener=opener)
    assert content_type == "image/jpeg"
    assert data.startswith(b"\xff\xd8")


def test_image_proxy_response_is_sandboxed_and_cacheable():
    flask_app = Flask(__name__)
    with flask_app.test_request_context("/image-proxy"):
        response = flask_app.response_class(b"img", mimetype="image/jpeg")
        response = add_security_headers(response, path="/image-proxy")
    assert "sandbox" in response.headers["Content-Security-Policy"]
    assert "script-src" not in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "public, max-age=86400"


# --- Google images URL hygiene ----------------------------------------------

def test_google_images_drop_non_https_thumbnails_and_unsafe_pages():
    import io
    import json

    payload = {
        "items": [
            {"title": "Dakar plage", "link": "https://a.example/1.jpg",
             "image": {"thumbnailLink": "http://t.example/1", "contextLink": "https://a.example/dakar"}},
            {"title": "Dakar corniche", "link": "https://a.example/2.jpg",
             "image": {"thumbnailLink": "https://t.example/2", "contextLink": "javascript:alert(1)"}},
            {"title": "Dakar ville", "link": "https://a.example/3.jpg",
             "image": {"thumbnailLink": "https://t.example/3", "contextLink": "https://a.example/dakar-ville"}},
        ]
    }

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        return Resp(json.dumps(payload).encode())

    images = fetch_google_images("Dakar", "key", "cx", limit=4, urlopen_fn=fake_urlopen)
    assert [item["display_url"] for item in images] == ["https://t.example/3"]


# --- Explorer ----------------------------------------------------------------

def test_explorer_page_escapes_knowledge_values():
    html = render_explorer_page(
        [{"name": 'Lieu "<script>x</script>', "region": "Dakar", "summary": 'a"b', "type": "site"}],
        [{"id": "dakar", "name": "<b>Dakar</b>"}],
    )
    assert "<script>x</script>" not in html
    assert "&lt;b&gt;Dakar&lt;/b&gt;" in html
    assert 'data-summary="a&quot;b"' in html


def test_explorer_image_results_are_cached_and_rate_guarded():
    calls = {"google": 0, "guard": 0}

    def google(query, limit=4):
        calls["google"] += 1
        return [{"url": "https://x/1.jpg", "display_url": "https://x/1.jpg"}]

    def guard(bucket):
        calls["guard"] += 1
        return None

    flask_app = Flask(__name__)
    register_explorer_routes(flask_app, {"places": [], "regions": []}, google, lambda *a, **k: [], lambda u: u, rate_guard=guard)
    client = flask_app.test_client()
    for _ in range(3):
        assert client.get("/explorer-image?query=Goree").get_json()["images"]
    assert calls == {"google": 1, "guard": 1}


def test_explorer_image_blocked_by_rate_guard():
    flask_app = Flask(__name__)

    def google(query, limit=4):
        raise AssertionError("Google should not be called when rate limited")

    def guard(bucket):
        return jsonify({"error": "limit"}), 429

    register_explorer_routes(flask_app, {"places": [], "regions": []}, google, lambda *a, **k: [], lambda u: u, rate_guard=guard)
    assert flask_app.test_client().get("/explorer-image?query=Goree").status_code == 429


# --- Trip planner ------------------------------------------------------------

class _NoOpenAI:
    class responses:
        @staticmethod
        def create(**kwargs):
            raise AssertionError("OpenAI must not be called when rate limited")


def _limited(bucket):
    return jsonify({"error": "limit", "bucket": bucket}), 429


def test_trip_planner_api_is_rate_guarded():
    flask_app = Flask(__name__)
    trip_planner.register_trip_planner(flask_app, _NoOpenAI(), "https://example.com", rate_guard=_limited)
    response = flask_app.test_client().post(
        "/api/trip-planner",
        json={"arrival": "2026-11-01", "departure": "2026-11-05"},
        headers={"Origin": "https://example.com"},
    )
    assert response.status_code == 429
    assert response.get_json()["bucket"] == "trip_planner"


def test_practical_info_api_is_rate_guarded():
    flask_app = Flask(__name__)
    trip_planner.register_trip_planner(flask_app, _NoOpenAI(), "https://example.com", rate_guard=_limited)
    response = flask_app.test_client().post(
        "/api/practical-info",
        json={"region": "Dakar", "category": "transport"},
        headers={"Origin": "https://example.com"},
    )
    assert response.status_code == 429
    assert response.get_json()["bucket"] == "practical_info"


def test_app_rate_guard_blocks_after_quota(monkeypatch):
    monkeypatch.setitem(app_module.GUARDED_LIMITS, "trip_planner", (2, 100))
    monkeypatch.setattr(app_module, "guarded_request_log", BoundedStore())
    monkeypatch.setattr(app_module, "redis_client", None)
    results = []
    for _ in range(3):
        with app_module.app.test_request_context("/", environ_base={"REMOTE_ADDR": "203.0.113.9"}):
            results.append(app_module.rate_guard("trip_planner"))
    assert results[0] is None and results[1] is None
    assert results[2][1] == 429
