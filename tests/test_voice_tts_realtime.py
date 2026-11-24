"""Voix : lecture à voix haute (/tts) et conversation vocale (/realtime-call), avec le fournisseur simulé."""

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
import fake_speech  # noqa: E402

B = "https://teranga-ai.fr"


def _client(ip):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    headers = {"X-CSRF-Token": token, "Origin": B}
    return client, headers, {"REMOTE_ADDR": ip}


def _fake_speech(monkeypatch, calls, fail=False, **options):
    return fake_speech.install(monkeypatch, app_module.client, calls, error="fournisseur indisponible" if fail else None, **options)


def test_tts_reads_clean_text_and_returns_audio(monkeypatch):
    calls = []
    _fake_speech(monkeypatch, calls)
    client, headers, env = _client("203.0.113.101")
    text = "## Titre\n- **Gorée** : voir [le site](https://exemple.sn/x) et https://exemple.sn\n1. Prendre la chaloupe"
    response = client.post("/tts", json={"text": text, "language": "zz"}, base_url=B, headers=headers, environ_base=env)
    assert response.status_code == 200 and response.mimetype == "audio/mpeg"
    assert response.data == b"".join(fake_speech.FAKE_MP3) and response.headers["Cache-Control"] == "no-store"
    spoken = calls[0]["input"]
    assert "http" not in spoken and "**" not in spoken and "##" not in spoken and "[" not in spoken
    assert "Gorée" in spoken and "le site" in spoken and "Prendre la chaloupe" in spoken
    assert len(calls) == 1


def test_tts_rejects_empty_text_and_reports_provider_failure(monkeypatch):
    calls = []
    _fake_speech(monkeypatch, calls)
    client, headers, env = _client("203.0.113.102")
    empty = client.post("/tts", json={"text": "   "}, base_url=B, headers=headers, environ_base=env)
    assert empty.status_code == 400 and calls == []
    _fake_speech(monkeypatch, calls, fail=True)
    failed = client.post("/tts", json={"text": "Bonjour"}, base_url=B, headers=headers, environ_base=env)
    assert failed.status_code == 502 and "voix" in failed.get_json()["error"]


def test_tts_is_rate_limited_per_minute(monkeypatch):
    calls = []
    _fake_speech(monkeypatch, calls)
    client, headers, env = _client("203.0.113.103")
    codes = [client.post("/tts", json={"text": "Bonjour"}, base_url=B, headers=headers, environ_base=env).status_code
             for _ in range(app_module.TTS_RATE_LIMIT + 2)]
    assert codes[0] == 200 and 429 in codes
    assert len(calls) <= app_module.TTS_RATE_LIMIT


class _Upstream:
    def __init__(self, body=b"v=0\r\nresponse-sdp"):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, _size=-1):
        return self.body


def _fake_openai(monkeypatch, captured, fail=False):
    import routes.realtime as realtime

    def fake_urlopen(req, timeout=0):
        captured.append(req)
        if fail:
            raise OSError("réseau")
        return _Upstream()

    monkeypatch.setattr(realtime, "urlopen", fake_urlopen)


def _realtime_app(limit=3):
    """Mini-application qui active la route (désactivée par défaut sur le vrai site)."""
    from flask import Flask

    from routes.realtime import register_realtime_route

    mini = Flask("realtime-test")
    mini.config["SECRET_KEY"] = app_module.app.config["SECRET_KEY"]
    names = ("origin_allowed", "valid_request_token", "valid_token", "CSRF_COOKIE", "CSRF_HEADER", "CSRF_TTL", "client_ip",
             "abuse_key", "abuse_blocked", "allowed_request", "record_abuse", "realtime_request_log", "realtime_hourly_log",
             "SAFE_LANG", "sanitize_text", "API_KEY")
    deps = {name: getattr(app_module, name) for name in names}
    deps.update(REALTIME_RATE_LIMIT=limit, REALTIME_HOURLY_LIMIT=50)
    register_realtime_route(mini, deps)
    return mini


def _mini_client(ip, limit=3):
    mini = _realtime_app(limit)
    token = app_module.app.test_client().get("/csrf", base_url=B).get_json()["token"]
    client = mini.test_client()
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    return client, {"X-CSRF-Token": token, "Origin": B}, {"REMOTE_ADDR": ip}


def test_realtime_voice_is_closed_by_default_on_the_real_site():
    # Une session vocale OpenAI est payante : la route n'existe que si REALTIME_VOICE_ENABLED=1.
    assert os.getenv("REALTIME_VOICE_ENABLED", "") != "1"
    client, headers, env = _client("203.0.113.109")
    assert client.post("/realtime-call", data={"sdp": "v=0"}, base_url=B, headers=headers, environ_base=env).status_code == 404


def test_realtime_call_needs_origin_and_csrf():
    client = _realtime_app().test_client()
    assert client.post("/realtime-call", data={"sdp": "v=0"}, base_url=B,
                       environ_base={"REMOTE_ADDR": "203.0.113.110"}).status_code == 403
    no_csrf = client.post("/realtime-call", data={"sdp": "v=0"}, base_url=B, headers={"Origin": B},
                          environ_base={"REMOTE_ADDR": "203.0.113.110"})
    assert no_csrf.status_code == 403 and no_csrf.get_json()["error"] == "csrf"


def test_realtime_call_builds_the_session_and_relays_the_answer(monkeypatch):
    captured = []
    _fake_openai(monkeypatch, captured)
    client, headers, env = _mini_client("203.0.113.111")
    response = client.post("/realtime-call", base_url=B, headers=headers, environ_base=env, data={
        "sdp": "v=0\r\noffer", "language": "wo", "audience": "inconnu", "context": "On parlait de Gorée."})
    assert response.status_code == 200 and response.mimetype == "application/sdp"
    assert response.data == b"v=0\r\nresponse-sdp" and response.headers["Cache-Control"] == "no-store"
    request_sent = captured[0]
    assert request_sent.full_url == "https://api.openai.com/v1/realtime/calls"
    assert request_sent.headers["Authorization"].startswith("Bearer ")
    body = request_sent.data.decode("utf-8")
    # Profil inconnu → « Tout le Sénégal » (avant : résident).
    assert "wolof" in body and "habitant, membre de la diaspora, commerçant ou voyageur" in body
    assert "On parlait de Gorée." in body and "v=0" in body


def test_realtime_call_rejects_invalid_sessions_and_reports_provider_failure(monkeypatch):
    captured = []
    _fake_openai(monkeypatch, captured)
    client, headers, env = _mini_client("203.0.113.112")
    assert client.post("/realtime-call", base_url=B, headers=headers, environ_base=env, data={"sdp": ""}).status_code == 400
    too_big = client.post("/realtime-call", base_url=B, headers=headers, environ_base=env, data={"sdp": "x" * 200_001})
    assert too_big.status_code == 400 and captured == []
    _fake_openai(monkeypatch, captured, fail=True)
    failed = client.post("/realtime-call", base_url=B, headers=headers, environ_base=env, data={"sdp": "v=0"})
    assert failed.status_code == 502 and "vocale" in failed.get_json()["error"]


def test_realtime_call_is_rate_limited(monkeypatch):
    captured = []
    _fake_openai(monkeypatch, captured)
    client, headers, env = _mini_client("203.0.113.113", limit=3)
    codes = [client.post("/realtime-call", base_url=B, headers=headers, environ_base=env, data={"sdp": "v=0"}).status_code
             for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and 429 in codes[3:]
    assert len(captured) == 3


def test_tts_has_its_own_short_timeout(monkeypatch):
    """Une lecture a échoué après 130,8 s le 13 octobre 2026 : sans délai propre, /tts héritait des 50 s du client
    OpenAI (app.py), avec une nouvelle tentative. Les lectures réussies ont toutes duré moins de 27 s (11-13 octobre)."""
    calls = []
    fake = _fake_speech(monkeypatch, calls)
    client, headers, env = _client("203.0.113.104")
    response = client.post("/tts", json={"text": "Bonjour"}, base_url=B, headers=headers, environ_base=env)
    assert response.status_code == 200
    delai = calls[0].get("timeout")
    assert delai is not None, "la voix doit avoir son propre délai"
    assert delai.read <= 30 and delai.connect <= 5
    # Sans nouvelle tentative : une seconde synthèse arriverait après l'abandon de la page.
    assert fake.options and fake.options[-1].get("max_retries") == 0


def test_tts_streams_compressed_audio_as_it_arrives(monkeypatch):
    # Premier son en moins de 3 s : le MP3 part vers le navigateur morceau par morceau,
    # sans attendre la fin de la génération (11 à 18 s en WAV, mesuré sur Render du 14 au 16 octobre).
    calls = []
    fake = _fake_speech(monkeypatch, calls)
    client, headers, env = _client("203.0.113.105")
    response = client.post("/tts", json={"text": "Bonjour"}, base_url=B, headers=headers, environ_base=env)
    assert response.status_code == 200 and response.is_streamed
    assert response.headers["X-Accel-Buffering"] == "no"
    assert calls[0]["response_format"] == "mp3"
    parts = list(response.response)
    assert parts[0] == fake_speech.FAKE_MP3[0] and b"".join(parts) == b"".join(fake_speech.FAKE_MP3)
    response.close()
    assert fake.state["closed"]


def test_tts_without_any_audio_is_a_failure(monkeypatch):
    calls = []
    fake = _fake_speech(monkeypatch, calls, chunks=())
    client, headers, env = _client("203.0.113.106")
    response = client.post("/tts", json={"text": "Bonjour"}, base_url=B, headers=headers, environ_base=env)
    assert response.status_code == 502 and "voix" in response.get_json()["error"]
    assert fake.state["closed"]


def test_tts_cut_mid_stream_keeps_what_was_sent(monkeypatch):
    calls = []
    fake = _fake_speech(monkeypatch, calls, late_error="coupure")
    client, headers, env = _client("203.0.113.107")
    response = client.post("/tts", json={"text": "Bonjour"}, base_url=B, headers=headers, environ_base=env)
    assert response.status_code == 200
    parts = iter(response.response)
    assert next(parts) == fake_speech.FAKE_MP3[0]  # le début part quand même
    # Puis l'erreur remonte : la connexion est coupée sans fin propre, la page ne met pas le son tronqué en cache.
    with pytest.raises(RuntimeError):
        next(parts)
    response.close()
    assert fake.state["closed"]
