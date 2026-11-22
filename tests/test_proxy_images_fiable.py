"""Ticket « proxy d'images Wikimedia » (audit du 22 novembre 2026) : « Erreur proxy image Wikimedia » dans les journaux
Render, portée inconnue.

Avant : toute erreur (404, 429, délai dépassé, réseau, mauvais type) donnait le même 502 et la même trace, et une image
cassée était redemandée à Wikimedia à chaque affichage. Maintenant : un journal court par cause, une réponse qui dit la
cause (404, 503 + Retry-After, 504, 502), et un souvenir borné des échecs pour ne pas insister.
"""

import io
import logging
import socket
from urllib.error import HTTPError, URLError

import pytest

import app as app_module
from services import image_failures

URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/{name}/500px-{name}"
_ip = iter(range(10, 250))


class FakeImage(io.BytesIO):
    def __init__(self, content_type="image/jpeg", body=b"fake-image"):
        super().__init__(body)
        self.headers = {"Content-Type": content_type}

    def get_content_type(self):
        return self.headers["Content-Type"]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def upstream(monkeypatch):
    """Faux Wikimedia : `upstream.answer` décide de la réponse ; `upstream.calls` compte les appels sortants."""
    image_failures.reset()

    class Upstream:
        calls = 0
        answer = staticmethod(lambda req: FakeImage())

        def open(self, req, timeout=None):
            Upstream.calls += 1
            return self.answer(req)

    fake = Upstream()
    monkeypatch.setattr(app_module._SAFE_IMAGE_OPENER, "open", fake.open)
    yield fake
    image_failures.reset()


def _get(name):
    """Chaque appel vient d'une adresse différente : la limite de débit par visiteur n'interfère pas."""
    from urllib.parse import quote

    client = app_module.app.test_client()
    return client.get("/image-proxy?url=" + quote(URL.format(name=name), safe=""),
                      environ_base={"REMOTE_ADDR": f"203.0.113.{next(_ip)}"})


def _http(code, headers=None):
    def answer(req):
        raise HTTPError(req.full_url, code, "erreur", headers or {}, None)
    return answer


def _raise(exc):
    def answer(req):
        raise exc
    return answer


def test_image_valide(upstream):
    response = _get("Dakar.jpg")
    assert response.status_code == 200 and response.data == b"fake-image"
    assert response.headers["Cache-Control"] == "public, max-age=86400"


@pytest.mark.parametrize("answer,status,kind", [
    (_http(404), 404, "introuvable"),
    (_http(410), 404, "introuvable"),
    (_http(429, {"Retry-After": "120"}), 503, "limite"),
    (_http(500), 502, "erreur-source"),
    (_http(503), 502, "erreur-source"),
    (_raise(socket.timeout("timed out")), 504, "delai"),
    (_raise(TimeoutError("timed out")), 504, "delai"),
    (_raise(URLError(socket.timeout("timed out"))), 504, "delai"),
    (_raise(URLError("Name or service not known")), 502, "reseau"),
    (_raise(ConnectionResetError()), 502, "reseau"),
    (lambda req: FakeImage("text/html"), 502, "type"),
    (lambda req: FakeImage(body=b"x" * (app_module.MAX_IMAGE_BYTES + 1)), 502, "trop-lourde"),
])
def test_chaque_cause_a_sa_reponse_et_un_journal_court(upstream, caplog, answer, status, kind):
    upstream.answer = answer
    with caplog.at_level(logging.WARNING):
        response = _get(f"{kind}-{status}-{id(answer)}.jpg")
    assert response.status_code == status
    lignes = [r for r in caplog.records if "proxy image" in r.getMessage()]
    assert len(lignes) == 1, [r.getMessage() for r in caplog.records]
    ligne = lignes[0]
    assert ligne.levelno == logging.WARNING and not ligne.exc_info  # cause connue : pas de trace complète
    message = ligne.getMessage()
    assert f"cause={kind}" in message and "hote=upload.wikimedia.org" in message and "ms" in message
    assert "203.0.113." not in message  # jamais l'adresse du visiteur


def test_limite_de_wikimedia_transmise_au_navigateur(upstream):
    upstream.answer = _http(429, {"Retry-After": "120"})
    response = _get("limite.jpg")
    assert response.status_code == 503 and response.headers["Retry-After"] == "120"
    upstream.answer = _http(429, {"Retry-After": "999999"})
    assert _get("limite-longue.jpg").headers["Retry-After"] == "300"  # borné
    upstream.answer = _http(429)
    assert _get("limite-sans-delai.jpg").headers["Retry-After"] == "60"


def test_une_image_cassee_n_est_pas_redemandee_a_chaque_affichage(upstream, caplog):
    upstream.answer = _http(404)
    with caplog.at_level(logging.WARNING):
        statuses = [_get("Cassee.jpg").status_code for _ in range(5)]
    assert statuses == [404] * 5
    assert upstream.calls == 1  # un seul appel sortant, puis le souvenir de l'échec répond
    assert len([r for r in caplog.records if "proxy image" in r.getMessage()]) == 1  # pas de journal en rafale


def test_le_souvenir_d_un_echec_expire(upstream, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(image_failures, "_now", lambda: now[0])
    upstream.answer = _raise(socket.timeout("timed out"))
    assert _get("Lente.jpg").status_code == 504
    upstream.answer = lambda req: FakeImage()
    assert _get("Lente.jpg").status_code == 504 and upstream.calls == 1  # encore en mémoire
    now[0] += image_failures.TTL["delai"] + 1
    assert _get("Lente.jpg").status_code == 200 and upstream.calls == 2  # la source est redemandée


def test_un_echec_ne_bloque_pas_les_autres_images(upstream):
    upstream.answer = _http(404)
    assert _get("Absente.jpg").status_code == 404
    upstream.answer = lambda req: FakeImage()
    assert _get("Presente.jpg").status_code == 200


def test_le_souvenir_des_echecs_reste_borne(upstream):
    upstream.answer = _http(404)
    for i in range(image_failures.MAX_ENTRIES + 50):
        image_failures.remember(URL.format(name=f"{i}.jpg"), "introuvable")
    assert image_failures.size() <= image_failures.MAX_ENTRIES


def test_une_erreur_inattendue_garde_sa_trace(upstream, caplog):
    upstream.answer = _raise(RuntimeError("bug"))
    with caplog.at_level(logging.WARNING):
        response = _get("Bug.jpg")
    assert response.status_code == 502
    lignes = [r for r in caplog.records if "proxy image" in r.getMessage()]
    assert len(lignes) == 1 and lignes[0].levelno == logging.ERROR and lignes[0].exc_info


@pytest.mark.parametrize("url,status", [
    ("https://evil.example/image.jpg", 400),
    ("https://upload.wikimedia.org/wikipedia/commons/x/Flag_of_Senegal.svg.png", 400),
    ("pas-une-url", 400),
    ("", 400),
])
def test_url_incorrecte_refusee_sans_appel_sortant(upstream, url, status):
    from urllib.parse import quote

    client = app_module.app.test_client()
    response = client.get("/image-proxy?url=" + quote(url, safe=""), environ_base={"REMOTE_ADDR": "203.0.113.251"})
    assert response.status_code == status and upstream.calls == 0
