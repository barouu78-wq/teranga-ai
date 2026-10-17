"""/tts en flux : le son part vers le visiteur dès les premiers octets du fournisseur (aucun appel réseau réel).

Mesures du 11 au 13 octobre 2026 (lignes « latence route=tts ») : médiane 15,3 s, p95 21,9 s, presque tout chez le
fournisseur. La route attendait le fichier WAV entier avant de répondre. Avec ``"flux": true`` elle demande au
fournisseur le format « pcm » en flux et relaie chaque morceau dès qu'il arrive.

Le VRAI SDK OpenAI est utilisé ici, avec un faux transport HTTP : on vérifie la forme réelle de l'appel
(``with_streaming_response``, format ``pcm``) et le relais morceau par morceau, sans clé ni réseau.
"""

import json
import os
import re
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from openai import OpenAI  # noqa: E402

try:  # le SDK OpenAI 3.x passe par httpx2 ; les versions précédentes par httpx
    import httpx2 as sdk_httpx  # noqa: E402
except ImportError:  # pragma: no cover - dépend de la version du SDK installée
    import httpx as sdk_httpx  # noqa: E402

import app as app_module  # noqa: E402
import latence_harness as h  # noqa: E402

B = "https://teranga-ai.fr"
ROOT = Path(__file__).resolve().parents[1]
SECOND = b"\x10\x00" * 2400  # 0,1 s de son à 24 000 Hz, 16 bits


class Upstream:
    """Faux fournisseur derrière le vrai SDK : un corps en morceaux, produit seulement quand on le lit."""

    def __init__(self, chunks=(SECOND, SECOND, SECOND), status=200, cut_after=None):
        self.chunks = list(chunks)
        self.status = status
        self.cut_after = cut_after  # coupure du fournisseur après ce nombre de morceaux
        self.produced = 0
        self.requests = []

    def _body(self):
        for index, chunk in enumerate(self.chunks):
            if self.cut_after is not None and index >= self.cut_after:
                raise sdk_httpx.ReadError("coupure du fournisseur")
            self.produced += 1
            yield chunk

    def handler(self, request):
        self.requests.append(json.loads(request.content))
        if self.status != 200:
            return sdk_httpx.Response(self.status, json={"error": {"message": "panne", "type": "server_error"}})
        return sdk_httpx.Response(200, headers={"Content-Type": "application/octet-stream"}, content=self._body())


def mini_client(upstream, ip):
    """La vraie route /tts, branchée sur un vrai client OpenAI dont le transport est simulé."""
    from flask import Flask

    from routes.tts import register_tts_route

    mini = Flask("tts-flux-test")
    mini.config["SECRET_KEY"] = app_module.app.config["SECRET_KEY"]
    names = ("require_json_post", "client_ip", "abuse_key", "abuse_blocked", "allowed_request", "record_abuse",
             "tts_request_log", "tts_hourly_log", "TTS_RATE_LIMIT", "TTS_HOURLY_LIMIT", "SAFE_LANG", "MAX_TTS_LENGTH",
             "sanitize_text")
    deps = {name: getattr(app_module, name) for name in names}
    transport = sdk_httpx.Client(transport=sdk_httpx.MockTransport(upstream.handler))
    # Comme le client partagé d'app.py, ce client refait une tentative ; /tts doit l'empêcher (with_options).
    deps["client"] = OpenAI(api_key="test-key", max_retries=1, http_client=transport)
    register_tts_route(mini, deps)
    token = app_module.app.test_client().get("/csrf", base_url=B).get_json()["token"]
    client = mini.test_client()
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    return client, {"X-CSRF-Token": token, "Origin": B}, {"REMOTE_ADDR": ip}


def post(client, headers, env, body):
    return client.post("/tts", json=body, base_url=B, headers=headers, environ_base=env, buffered=False)


def test_flux_relays_the_first_sound_before_the_provider_has_finished():
    """Avant : la route attendait tout le fichier (les trois morceaux) avant d'envoyer le moindre octet."""
    upstream = Upstream()
    client, headers, env = mini_client(upstream, "203.0.113.230")
    response = post(client, headers, env, {"text": "Bonjour Dakar.", "language": "fr", "flux": True})
    assert response.status_code == 200 and response.mimetype == "audio/pcm"
    assert response.headers["Cache-Control"] == "no-store" and response.headers["X-Accel-Buffering"] == "no"
    body = iter(response.response)
    first = next(body)
    assert first == SECOND
    assert upstream.produced == 1, "le premier son doit partir avant que le fournisseur ait tout produit"
    rest = b"".join(body)
    assert upstream.produced == 3 and first + rest == SECOND * 3  # rien de perdu, rien de répété
    response.close()


def test_flux_sends_the_provider_exactly_the_same_text_and_settings_as_the_file():
    """Même coût pour un même texte : mêmes caractères, mêmes consignes de voix, un seul appel ; seul le format change."""
    upstream = Upstream()
    client, headers, env = mini_client(upstream, "203.0.113.231")
    text = "## Gorée\n- **Chaloupe** : voir [le site](https://exemple.sn/x). Départ du port de Dakar."
    post(client, headers, env, {"text": text, "language": "fr", "flux": True}).close()
    post(client, headers, env, {"text": text, "language": "fr"}).close()
    assert len(upstream.requests) == 2, "un appel au fournisseur par requête /tts, en flux comme en fichier"
    streamed, whole = upstream.requests
    assert streamed["response_format"] == "pcm" and whole["response_format"] == "wav"
    assert {k: v for k, v in streamed.items() if k != "response_format"} == {k: v for k, v in whole.items() if k != "response_format"}
    assert len(streamed["input"]) == len(whole["input"]) and "http" not in streamed["input"] and "**" not in streamed["input"]


def test_flux_only_when_asked_with_true():
    upstream = Upstream()
    client, headers, env = mini_client(upstream, "203.0.113.232")
    for value in ("oui", 1, None):
        response = post(client, headers, env, {"text": "Bonjour", "flux": value})
        assert response.status_code == 200 and response.mimetype == "audio/wav", value
        response.close()
    assert [r["response_format"] for r in upstream.requests] == ["wav", "wav", "wav"]


def test_a_provider_failure_before_any_sound_is_a_clean_502():
    """La réponse n'est envoyée qu'une fois le premier son reçu : une panne reste un 502 lisible, comme avant."""
    failing = Upstream(status=500)
    client, headers, env = mini_client(failing, "203.0.113.233")
    response = post(client, headers, env, {"text": "Bonjour", "flux": True})
    assert response.status_code == 502 and "voix" in response.get_json()["error"]
    assert len(failing.requests) == 1, "sans nouvelle tentative, en flux comme en fichier"
    silent = Upstream(chunks=())
    client, headers, env = mini_client(silent, "203.0.113.234")
    response = post(client, headers, env, {"text": "Bonjour", "flux": True})
    assert response.status_code == 502 and "voix" in response.get_json()["error"]


def test_a_stream_cut_by_the_provider_ends_early_and_is_logged_as_an_error():
    lines = h.capture_lines()
    try:
        upstream = Upstream(cut_after=1)
        client, headers, env = mini_client(upstream, "203.0.113.235")
        response = post(client, headers, env, {"text": "Bonjour", "flux": True})
        assert response.status_code == 200
        assert b"".join(response.response) == SECOND  # ce qui est arrivé est relayé, puis le flux se ferme
        response.close()
    finally:
        h.release_lines(lines)
    (line,) = [entry for entry in lines.lines if entry.startswith("latence route=tts")]
    assert h.fields(line)["statut"] == "erreur" and h.fields(line)["mode"] == "flux"


def test_flux_counts_in_the_same_rate_limits_and_keeps_the_csrf_check():
    upstream = Upstream()
    client, headers, env = mini_client(upstream, "203.0.113.236")
    codes = []
    for _ in range(app_module.TTS_RATE_LIMIT + 2):
        response = post(client, headers, env, {"text": "Bonjour", "flux": True})
        codes.append(response.status_code)
        response.close()
    assert codes[0] == 200 and 429 in codes
    assert len(upstream.requests) <= app_module.TTS_RATE_LIMIT
    no_token = client.post("/tts", json={"text": "Bonjour", "flux": True}, base_url=B, headers={"Origin": B},
                           environ_base={"REMOTE_ADDR": "203.0.113.237"})
    assert no_token.status_code == 403
    assert len(upstream.requests) <= app_module.TTS_RATE_LIMIT


def test_the_real_app_streams_without_compression(monkeypatch):
    """Dans la vraie application, la compression gzip ne doit pas retenir le flux audio."""
    fake = h.install_speech_stream(monkeypatch)
    client, headers, env = h.make_client()
    headers["Accept-Encoding"] = "gzip"
    response = client.post("/tts", json={"text": "Bonjour", "flux": True}, base_url=B, headers=headers,
                           environ_base=env, buffered=False)
    assert response.status_code == 200 and response.is_streamed and response.mimetype == "audio/pcm"
    assert "Content-Encoding" not in response.headers
    assert b"".join(response.response) == b"".join(fake.chunks)
    response.close()
    assert fake.calls[0]["response_format"] == "pcm" and fake.calls[0]["timeout"].read <= 30
    assert fake.options and fake.options[-1].get("max_retries") == 0  # sans nouvelle tentative
    assert fake.closed == 1, "la connexion au fournisseur doit être fermée à la fin du flux"


def test_the_page_and_the_server_agree_on_the_sound_format():
    from routes.tts import TTS_PCM_RATE

    source = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
    declared = re.search(r"const VOICE_PCM_RATE=(\d+);", source)
    assert declared and int(declared.group(1)) == TTS_PCM_RATE == 24000
