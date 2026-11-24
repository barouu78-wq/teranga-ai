"""Google refuse l'accès au projet (403 « does not have the access ») : ce n'est pas un quota.

Constat de production (journaux Render, 16-18 octobre 2026) : chaque fin de pause de 6 h relançait des appels
voués au même refus, et chaque refus vidait tout le corps JSON de l'erreur, en double, dans les journaux. La
Custom Search JSON API est fermée aux nouveaux clients (fin annoncée au 1er janvier 2027) : un refus d'accès
doit couper Google longtemps, une ligne de journal suffit, et changer la clé ou le cx doit relancer l'essai.
"""

import hashlib
import io
import json
import logging
import os
from urllib.error import HTTPError

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services import images  # noqa: E402

REFUS_ACCES = {
    "error": {
        "code": 403,
        "message": "This project does not have the access to Custom Search JSON API.",
        "errors": [{"message": "This project does not have the access to Custom Search JSON API.",
                    "domain": "global", "reason": "forbidden"}],
        "status": "PERMISSION_DENIED",
    }
}
QUOTA_JOUR = {
    "error": {
        "code": 403,
        "message": "Quota exceeded for quota metric 'Queries' and limit 'Queries per day'.",
        "errors": [{"message": "Quota exceeded", "domain": "usageLimits", "reason": "dailyLimitExceeded"}],
        "status": "PERMISSION_DENIED",
    }
}


def _http_error(code, body):
    return HTTPError("https://www.googleapis.com/customsearch/v1", code, "Forbidden", {},
                     io.BytesIO(json.dumps(body).encode("utf-8")))


class FakeRedis:
    def __init__(self):
        self.data, self.ttls = {}, {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key], self.ttls[key] = value, ttl


@pytest.fixture
def google(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(app_module, "GOOGLE_API_KEY", "cle-de-test-123")
    monkeypatch.setattr(app_module, "GOOGLE_CSE_ID", "cx-test")
    monkeypatch.setattr(app_module, "redis_client", redis)
    monkeypatch.setattr(app_module, "_google_paused_until", 0.0)
    monkeypatch.setattr(app_module, "_google_checked_until", 0.0)
    monkeypatch.setattr(app_module, "_google_pause_reason", "")
    return redis


def _refuse_with(monkeypatch, body, code=403):
    calls = []

    def opener(req, timeout=8):
        calls.append(req.full_url)
        raise _http_error(code, body)

    monkeypatch.setattr(app_module, "urlopen", opener)
    return calls


def test_refus_d_acces_coupe_google_sept_jours_et_pas_six_heures(monkeypatch, google):
    calls = _refuse_with(monkeypatch, REFUS_ACCES)
    assert app_module.fetch_google_images("Île de Gorée Sénégal") == []
    assert app_module.google_images_status() == "access_denied"
    (ttl,) = google.ttls.values()
    assert ttl >= 7 * 24 * 3600
    assert app_module.fetch_google_images("Lac Rose Sénégal") == []
    assert len(calls) == 1


def test_quota_du_jour_reste_une_pause_courte(monkeypatch, google):
    _refuse_with(monkeypatch, QUOTA_JOUR)
    assert app_module.fetch_google_images("Dakar") == []
    assert app_module.google_images_status() == "paused"
    (ttl,) = google.ttls.values()
    assert ttl == app_module.GOOGLE_PAUSE_SECONDS


def test_changer_la_cle_ou_le_cx_relance_l_essai(monkeypatch, google):
    _refuse_with(monkeypatch, REFUS_ACCES)
    app_module.fetch_google_images("Dakar")
    assert app_module.google_images_paused()
    # Le propriétaire configure un autre projet Google : la pause de l'ancien ne doit pas s'appliquer.
    monkeypatch.setattr(app_module, "GOOGLE_CSE_ID", "autre-cx")
    monkeypatch.setattr(app_module, "_google_paused_until", 0.0)
    monkeypatch.setattr(app_module, "_google_checked_until", 0.0)
    assert not app_module.google_images_paused()


def test_une_seule_ligne_de_journal_sans_cle_ni_json(monkeypatch, google, caplog, capsys):
    _refuse_with(monkeypatch, REFUS_ACCES)
    with caplog.at_level(logging.DEBUG):
        app_module.fetch_google_images("Île de Ngor Dakar")
    google_lines = [r.getMessage() for r in caplog.records if "google" in r.getMessage().lower()]
    # Une ligne au total par refus (relecture de #494 : services/images.py et app.py en écrivaient chacun une).
    assert len(google_lines) == 1, google_lines
    (line,) = google_lines
    assert "\n" not in line
    assert "cle-de-test-123" not in line
    assert '"errors"' not in line
    # La ligne unique garde tout le diagnostic : code, raison de Google, message et durée de la pause.
    assert "403" in line and "forbidden" in line and "does not have the access" in line
    assert "168 h" in line
    assert capsys.readouterr().out == "", "plus de print() : il doublait chaque ligne dans Render"


def test_un_quota_ecrit_aussi_une_seule_ligne(monkeypatch, google, caplog):
    _refuse_with(monkeypatch, QUOTA_JOUR)
    with caplog.at_level(logging.DEBUG):
        app_module.fetch_google_images("Dakar")
    google_lines = [r.getMessage() for r in caplog.records if "google" in r.getMessage().lower()]
    assert len(google_lines) == 1, google_lines
    assert "dailyLimitExceeded" in google_lines[0] and "6 h" in google_lines[0]


def test_le_nom_de_la_pause_ne_derive_pas_la_cle_par_un_hachage_rapide(google):
    # Alerte CodeQL de #494 : un SHA-256 simple de la clé API permettrait de tester des clés candidates très vite.
    nom = app_module._google_pause_key()
    sha256_simple = hashlib.sha256(b"cle-de-test-123|cx-test").hexdigest()[:16]
    assert "cle-de-test-123" not in nom
    assert sha256_simple not in nom
    assert nom == app_module._google_pause_key(), "même configuration, même pause (tous les workers)"


def test_changer_la_cle_api_relance_aussi_l_essai(monkeypatch, google):
    _refuse_with(monkeypatch, REFUS_ACCES)
    app_module.fetch_google_images("Dakar")
    monkeypatch.setattr(app_module, "GOOGLE_API_KEY", "nouvelle-cle-456")
    monkeypatch.setattr(app_module, "_google_paused_until", 0.0)
    monkeypatch.setattr(app_module, "_google_checked_until", 0.0)
    assert not app_module.google_images_paused()


def test_l_erreur_porte_la_raison_lisible_pour_l_appelant():
    def opener(req, timeout=8):
        raise _http_error(403, REFUS_ACCES)

    with pytest.raises(HTTPError) as caught:
        images.fetch_google_images("Dakar", "cle-de-test-123", "cx-test", urlopen_fn=opener)
    assert caught.value.google_status == "PERMISSION_DENIED"
    assert caught.value.google_reason == "forbidden"
    assert "does not have the access" in caught.value.google_message


def test_health_dit_que_google_refuse_l_acces(monkeypatch, google):
    _refuse_with(monkeypatch, REFUS_ACCES)
    app_module.fetch_google_images("Dakar")
    data = app_module.app.test_client().get("/health").get_json()
    assert data["google_images"] == "access_denied"


def test_un_worker_qui_lit_la_pause_dans_redis_n_appelle_plus_google(monkeypatch, google):
    """Constat de production (journaux Render, 17-24 octobre 2026) : chaque worker refaisait son propre appel refusé.

    Après avoir lu la pause dans Redis, un worker répondait « en pause » une fois, puis « pas en pause » pendant 60 s
    (il ne relit Redis qu'une fois par minute) : une demande de photos dans cette fenêtre, rouverte par chaque
    /health d'UptimeRobot, appelait Google et écrivait une nouvelle ligne « en pause 168 h ».
    """
    google.setex(app_module._google_pause_key(), app_module.GOOGLE_ACCESS_DENIED_PAUSE_SECONDS, "access_denied")
    calls = _refuse_with(monkeypatch, REFUS_ACCES)
    assert app_module.google_images_status() == "access_denied"  # /health lit la pause dans Redis
    assert app_module.fetch_google_images("Île de Gorée Sénégal") == []
    assert app_module.google_images_paused()
    assert calls == []


def test_la_fin_de_la_pause_dans_redis_est_vue_dans_la_minute(monkeypatch, google):
    clock = {"now": 1_000_000.0}
    monkeypatch.setattr(app_module.time, "time", lambda: clock["now"])
    google.setex(app_module._google_pause_key(), app_module.GOOGLE_PAUSE_SECONDS, "paused")
    assert app_module.google_images_paused()
    google.data.clear()  # la pause expire dans Redis
    clock["now"] += 30
    assert app_module.google_images_paused(), "une lecture de Redis par minute au plus"
    clock["now"] += 31
    assert not app_module.google_images_paused()


def test_sans_cle_google_le_statut_reste_missing(monkeypatch):
    monkeypatch.setattr(app_module, "GOOGLE_API_KEY", "")
    assert app_module.google_images_status() == "missing"
