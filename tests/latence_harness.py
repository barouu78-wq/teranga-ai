"""Outils communs aux tests de latence : faux fournisseur, client avec CSRF, capture des lignes de journal.

Le faux fournisseur remplace `client.responses.create` (et les appels audio) : tout le reste (construction de la
requête, route, flux) est le code réel. Aucun appel réseau.
"""

import io
import itertools
import logging
import os
import time
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.pop("ANTHROPIC_API_KEY", None)

import app as app_module  # noqa: E402
import fake_speech  # noqa: E402
from services import latency  # noqa: E402

B = "https://teranga-ai.fr"
_COUNTER = itertools.count(1)


def next_ip():
    """Une adresse (plage de documentation RFC 5737) par requête de test : les limites de débit restent indépendantes."""
    return f"192.0.2.{next(_COUNTER) % 250 + 1}"


class Capture(logging.Handler):
    """Récupère les lignes écrites par le journal de latence."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def capture_lines():
    handler = Capture()
    latency.get_logger().addHandler(handler)
    return handler


def release_lines(handler):
    latency.get_logger().removeHandler(handler)


def fields(line):
    """{'route': 'chat', 'total_ms': '12.3', …} à partir d'une ligne `latence route=… clé=valeur …`."""
    assert line.startswith("latence "), line
    return dict(pair.split("=", 1) for pair in line.split()[1:])


# --- Faux fournisseur de texte ---------------------------------------------------------------------------


def delta(text):
    return SimpleNamespace(type="response.output_text.delta", delta=text)


def completed(text):
    return SimpleNamespace(type="response.completed", response=SimpleNamespace(status="completed", incomplete_details=None, output_text=text, output=[]))


def incomplete(text):
    details = SimpleNamespace(reason="max_output_tokens")
    return SimpleNamespace(type="response.incomplete", response=SimpleNamespace(status="incomplete", incomplete_details=details, output_text=text))


def failed():
    return SimpleNamespace(type="response.failed", response=SimpleNamespace(error=SimpleNamespace(message="échec simulé", code="x")))


def full(text):
    return SimpleNamespace(output_text=text, status="completed", incomplete_details=None, output=[])


class Provider:
    """Remplace `client.responses.create` : flux (stream=True) ou réponse complète (stream=False)."""

    def __init__(self, events=None, full_reply=None, error=None, pause=0.0, first_pause=0.0):
        self.events = events or []
        self.full_reply = full_reply
        self.error = error  # message de l'exception levée par le fournisseur
        self.pause = pause  # attente avant de rendre la main (connexion au fournisseur)
        self.first_pause = first_pause  # attente avant le premier événement du flux
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(bool(kwargs.get("stream")))
        if self.pause:
            time.sleep(self.pause)
        if self.error:
            raise RuntimeError(self.error)
        if kwargs.get("stream"):
            return self._stream()
        return self.full_reply if self.full_reply is not None else full("")

    def _stream(self):
        if self.first_pause:
            time.sleep(self.first_pause)
        yield from self.events


def install_provider(monkeypatch, **kwargs):
    fake = Provider(**kwargs)
    monkeypatch.setattr(app_module.client.responses, "create", fake)
    return fake


# --- Requêtes ---------------------------------------------------------------------------------------------


def make_client(ip=None, *, identity=None):
    client = app_module.app.test_client()
    token = client.get("/csrf", base_url=B).get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    if identity:
        client.set_cookie(app_module.IDENTITY_COOKIE, identity, domain="teranga-ai.fr")
    return client, {"X-CSRF-Token": token, "Origin": B}, {"REMOTE_ADDR": ip or next_ip()}


def post_chat(message, *, ip=None, json_mode=False, history=None, identity=None, language="fr"):
    """Réponse NON lue : l'appelant la termine avec `finish` (le serveur WSGI ferme la réponse, le client de test non)."""
    client, headers, environ = make_client(ip, identity=identity)
    if json_mode:
        headers["X-Teranga-Mode"] = "json"
    turns = history if history is not None else [{"role": "user", "content": message}]
    body = {"message": message, "history": turns, "language": language, "audience": "tourist"}
    return client.post("/chat", json=body, headers=headers, base_url=B, environ_base=environ)


def finish(response):
    """Lit toute la réponse puis la ferme, comme le fait le serveur WSGI ; renvoie les octets du corps."""
    data = response.get_data()
    response.close()
    return data


def snapshot(response):
    """Tout ce que voit le visiteur : statut, corps (octets) et en-têtes utiles."""
    data = finish(response)
    names = ("Content-Type", "Cache-Control", "Retry-After", "X-Accel-Buffering", "Content-Encoding")
    return {"status": response.status_code, "body": data, "headers": {name: response.headers.get(name) for name in names}}


# --- Voix -------------------------------------------------------------------------------------------------


def post_stt(*, ip=None, audio=b"RIFF\x00\x00\x00\x00WAVEfake", text="bonjour", error=None, context="", monkeypatch=None):
    def create(**kwargs):
        if error:
            raise RuntimeError(error)
        return SimpleNamespace(text=text)

    monkeypatch.setattr(app_module.client.audio.transcriptions, "create", create)
    client = app_module.app.test_client()
    token = client.get("/csrf").get_json()["token"]
    data = {"language": "fr", "context": context}
    if audio is not None:
        data["audio"] = (io.BytesIO(audio), "voix.webm")
    return client.post(
        "/stt", data=data, content_type="multipart/form-data",
        headers={"Origin": app_module.SITE_URL, "X-CSRF-Token": token}, environ_base={"REMOTE_ADDR": ip or next_ip()},
    )


def post_tts(text="Bonjour", *, ip=None, error=None, monkeypatch=None, late_error=None):
    fake_speech.install(monkeypatch, app_module.client, [], error=error, late_error=late_error)
    client, headers, environ = make_client(ip)
    response = client.post("/tts", json={"text": text, "language": "fr"}, headers=headers, base_url=B, environ_base=environ)
    try:
        response.get_data()  # le son arrive en flux : le visiteur l'écoute jusqu'au bout (sinon la ligne dirait « abandon »)
    except RuntimeError:
        if not late_error:
            raise  # seule la coupure demandée par le test peut interrompre le flux
    return response
