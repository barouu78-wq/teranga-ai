"""Deux chemins de la production que les tests n'exécutaient pas (audit du 25 novembre 2026).

1. Claude est l'IA principale en production (AI_PRINCIPALE=claude). Hors flux (nouvelle tentative quand le flux n'a
   rien donné, chat sans flux), create_response appelle claude_response, puis OpenAI si Claude échoue : jamais testé.
2. Les clics partenaires (/go/…) sont comptés dans Redis en production ; les tests ne passaient que par la mémoire.
   Ces chiffres s'affichent sur /stats-partenaires, montrée aux partenaires.
"""

import datetime as dt
import logging
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from services import chat_service as chat_service_module  # noqa: E402
from services.click_stats import ClickStats  # noqa: E402


# --- 1. Claude principal, hors flux -------------------------------------------------------------------------------

def _service(openai_calls):
    def openai_stub(client, payload, **kw):
        openai_calls.append(kw.get("stream"))
        return SimpleNamespace(output_text="Réponse OpenAI de relais.", sources=[])

    return chat_service_module.build_chat_service(
        client=None, model="m", logger=logging.getLogger("test"), build_model_kwargs=lambda *a, **k: {},
        reasoning_effort=None, search_context_size=None, preferred_domains=None,
        create_openai_response=openai_stub, clean_answer=lambda t: t, extract_sources=lambda *a: [],
        fetch_topic_images=None, lookup_map=None, should_fetch_map=None,
    )


@pytest.fixture
def claude_principal(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_PRINCIPALE", "claude")


def test_hors_flux_claude_principal_repond(monkeypatch, claude_principal):
    monkeypatch.setattr(chat_service_module, "claude_response",
                        lambda prompt, **kw: SimpleNamespace(output_text="Réponse de Claude.", sources=[]))
    calls = []
    response = _service(calls)["create_response"]({"message": "Q", "input_text": "Q"}, False)
    assert response.output_text == "Réponse de Claude." and calls == []


def test_hors_flux_claude_en_panne_openai_prend_le_relais(monkeypatch, claude_principal):
    def panne(prompt, **kw):
        raise RuntimeError("Claude overloaded")

    monkeypatch.setattr(chat_service_module, "claude_response", panne)
    calls = []
    response = _service(calls)["create_response"]({"message": "Q", "input_text": "Q"}, False)
    assert response.output_text == "Réponse OpenAI de relais." and calls == [False]


def test_hors_flux_une_photo_n_est_jamais_envoyee_a_openai(monkeypatch, claude_principal):
    def panne(prompt, **kw):
        raise RuntimeError("Claude overloaded")

    monkeypatch.setattr(chat_service_module, "claude_response", panne)
    calls = []
    with pytest.raises(RuntimeError):
        _service(calls)["create_response"]({"message": "Q", "input_text": "Q", "fichier": {"bloc": {"type": "image"}}},
                                           False)
    assert calls == []  # OpenAI répondrait sans avoir vu la photo


# --- 2. Clics partenaires dans Redis ------------------------------------------------------------------------------

class FauxRedis:
    """Juste ce que ClickStats utilise : hachages, durée de vie et pipeline."""

    def __init__(self):
        self.hashes, self.ttl, self.panne = {}, {}, False

    def _verifier(self):
        if self.panne:
            raise ConnectionError("Redis injoignable")

    def hincrby(self, key, field, n):
        self._verifier()
        h = self.hashes.setdefault(key, {})
        h[field] = h.get(field, 0) + n

    def expire(self, key, seconds):
        self._verifier()
        self.ttl[key] = seconds

    def hexists(self, key, field):
        self._verifier()
        return field in self.hashes.get(key, {})

    def hlen(self, key):
        self._verifier()
        return len(self.hashes.get(key, {}))

    def hgetall(self, key):
        self._verifier()
        # Comme en production (app.py : decode_responses=True) : clés et valeurs en texte.
        return {k: str(v) for k, v in self.hashes.get(key, {}).items()}

    def pipeline(self, transaction=False):
        redis, ops = self, []

        class Pipe:
            def hincrby(self, *a):
                ops.append(("hincrby", a))

            def expire(self, *a):
                ops.append(("expire", a))

            def execute(self):
                for name, args in ops:
                    getattr(redis, name)(*args)

        return Pipe()


JOUR = dt.date(2026, 11, 25)


def test_les_clics_sont_comptes_dans_redis_et_relus():
    redis = FauxRedis()
    stats = ClickStats(redis_client=redis)
    for _ in range(3):
        stats.record("booking", "lieux", day=JOUR)
    stats.record("gyg", "accueil", day=JOUR)
    assert redis.hashes["teranga:clicks:2026-11"] == {"booking|lieux": 3, "gyg|accueil": 1}
    assert redis.ttl["teranga:clicks:2026-11"] > 365 * 24 * 3600  # l'historique survit un an
    assert stats.month_counts("2026-11") == {"booking|lieux": 3, "gyg|accueil": 1}
    assert stats._memory == {}  # rien en mémoire quand Redis répond


def test_au_dela_de_la_limite_une_nouvelle_origine_compte_autre():
    redis = FauxRedis()
    stats = ClickStats(redis_client=redis)
    stats.record("widget", "hotel-a", day=JOUR, max_fields=2)
    stats.record("widget", "hotel-b", day=JOUR, max_fields=2)
    stats.record("widget", "invente-par-un-script", day=JOUR, max_fields=2)
    stats.record("widget", "hotel-a", day=JOUR, max_fields=2)  # origine déjà connue : toujours comptée
    assert redis.hashes["teranga:clicks:2026-11"] == {"widget|hotel-a": 2, "widget|hotel-b": 1, "widget|autre": 1}


def test_redis_en_panne_les_clics_ne_sont_pas_perdus():
    redis = FauxRedis()
    stats = ClickStats(redis_client=redis)
    stats.record("booking", "lieux", day=JOUR)
    redis.panne = True
    stats.record("booking", "lieux", day=JOUR)  # compté en mémoire pendant la panne
    redis.panne = False
    assert stats.month_counts("2026-11") == {"booking|lieux": 2}
