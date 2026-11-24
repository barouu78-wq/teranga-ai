"""Plafond global de dépense IA : un nombre d'appels payants par jour pour tout le site (audit V3, P1-4).

Les limites par adresse IP ne bornent pas la facture quand beaucoup d'adresses appellent en même temps.
Choix du propriétaire (26 octobre 2026) : 500 appels par jour (AI_PLAFOND_JOUR). Au-delà, jusqu'à minuit
(heure de Dakar = UTC) : le chat répond avec la base vérifiée, sans IA ni recherche web ; la voix et le
planificateur répondent 503 avec un message clair. Aucun appel réseau.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from latence_harness import B, app_module, finish, install_provider, next_ip, post_chat, post_stt, post_tts

from services.ai_budget import DEFAULT_DAILY_LIMIT, AiBudget, daily_limit

JOUR = datetime(2026, 10, 26, 22, 0, tzinfo=timezone.utc)


class _Redis:
    def __init__(self, broken=False):
        self.values, self.ttl, self.broken = {}, {}, broken

    def incr(self, key):
        if self.broken:
            raise ConnectionError("Redis indisponible (simulé)")
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.ttl[key] = seconds


class _Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


@pytest.mark.parametrize("raw,expected", [("", DEFAULT_DAILY_LIMIT), ("abc", DEFAULT_DAILY_LIMIT), ("0", DEFAULT_DAILY_LIMIT),
                                          ("-5", DEFAULT_DAILY_LIMIT), (" 200 ", 200), ("1000", 1000)])
def test_daily_limit_reads_the_setting_and_falls_back_to_500(raw, expected):
    assert DEFAULT_DAILY_LIMIT == 500
    assert daily_limit(raw) == expected


def test_shared_counter_stops_at_the_limit_and_expires():
    redis = _Redis()
    budget = AiBudget(redis, limit=3, now=_Clock(JOUR))
    assert [budget.take() for _ in range(5)] == [True, True, True, False, False]
    assert redis.ttl and all(seconds >= 86400 for seconds in redis.ttl.values())  # la clé du jour disparaît seule


def test_counter_starts_again_at_midnight():
    clock = _Clock(JOUR)
    budget = AiBudget(_Redis(), limit=1, now=clock)
    assert budget.take() and not budget.take()
    assert budget.retry_after() == 2 * 3600  # 22 h UTC : minuit dans 2 heures
    clock.now = JOUR + timedelta(hours=2)
    assert budget.take()


def test_without_redis_each_process_still_counts():
    for redis in (None, _Redis(broken=True)):
        budget = AiBudget(redis, limit=2, now=_Clock(JOUR), processes=1)
        assert [budget.take() for _ in range(3)] == [True, True, False]


def test_redis_outage_keeps_the_count_already_used_today():
    redis = _Redis()
    budget = AiBudget(redis, limit=4, now=_Clock(JOUR), processes=1)
    assert [budget.take() for _ in range(3)] == [True, True, True]
    redis.broken = True  # Redis tombe en panne après 3 appels : le processus repart de 3, pas de 0
    assert [budget.take() for _ in range(2)] == [True, False]


# Ticket « plafond sans Redis » (audit du 22 novembre 2026) : sans Redis, chaque processus de Gunicorn comptait seul
# jusqu'au plafond, si bien que le site pouvait faire « plafond × processus » requêtes par jour (1 000 au lieu de 500
# avec les 2 processus par défaut). Maintenant chaque processus suppose que les autres dépensent comme lui.

@pytest.mark.parametrize("redis", [None, "panne"])
@pytest.mark.parametrize("processes", [1, 2, 3, 4])
def test_sans_redis_le_total_de_tous_les_processus_reste_sous_le_plafond(redis, processes):
    limit = 500
    shared = _Redis(broken=True) if redis else None
    workers = [AiBudget(shared, limit=limit, now=_Clock(JOUR), processes=processes) for _ in range(processes)]
    accepted = 0
    for _ in range(limit * 2):  # chaque processus reçoit autant de requêtes, bien plus que le plafond
        accepted += sum(worker.take() for worker in workers)
    assert limit - processes < accepted <= limit


def test_panne_de_redis_en_cours_de_journee_le_reste_du_plafond_est_partage():
    """300 requêtes déjà comptées par Redis, puis panne : il reste 200 pour la journée, partagées par 2 processus."""
    redis = _Redis()
    workers = [AiBudget(redis, limit=500, now=_Clock(JOUR), processes=2) for _ in range(2)]
    for _ in range(150):
        assert workers[0].take() and workers[1].take()
    redis.broken = True
    accepted = 0
    for _ in range(1000):
        accepted += sum(worker.take() for worker in workers)
    assert 300 + accepted <= 500 and accepted >= 198


def test_redis_revenu_le_compte_partage_reprend():
    redis = _Redis()
    budget = AiBudget(redis, limit=10, now=_Clock(JOUR), processes=2)
    redis.broken = True
    assert [budget.take() for _ in range(6)] == [True] * 5 + [False]
    redis.broken = False  # Redis revient : son propre compte (0 ici) fait foi de nouveau
    assert budget.take()


def test_le_nombre_de_processus_vient_de_gunicorn(monkeypatch):
    from services.ai_budget import worker_count

    for raw, expected in (("", 2), ("3", 3), ("0", 2), ("-1", 2), ("abc", 2), (" 4 ", 4)):
        monkeypatch.setenv("GUNICORN_WORKERS", raw)
        assert worker_count() == expected, raw
    monkeypatch.setenv("GUNICORN_WORKERS", "3")
    assert AiBudget(None, limit=9, now=_Clock(JOUR)).processes == 3


def test_le_jour_suivant_le_compte_local_repart_de_zero():
    clock = _Clock(JOUR)
    budget = AiBudget(None, limit=4, now=clock, processes=2)
    assert [budget.take() for _ in range(3)] == [True, True, False]
    clock.now = JOUR + timedelta(hours=2)  # minuit passé
    assert budget.take()


def test_a_failed_expire_does_not_count_twice_and_is_retried():
    """Audit de sécurité du 1er novembre 2026 (constat 6) : si EXPIRE échoue après un INCR réussi, la requête
    comptait aussi en local (deux fois) et la clé du jour restait sans durée de vie."""

    class _ExpireFails(_Redis):
        def __init__(self):
            super().__init__()
            self.expire_calls = 0

        def expire(self, key, seconds):
            self.expire_calls += 1
            if self.expire_calls == 1:
                raise ConnectionError("EXPIRE refusé (simulé)")
            super().expire(key, seconds)

    redis = _ExpireFails()
    budget = AiBudget(redis, limit=2, now=_Clock(JOUR))
    assert [budget.take() for _ in range(3)] == [True, True, False]  # 3 requêtes, comptées une seule fois chacune
    assert budget._memory_count == 3  # le compteur local suit Redis, sans double comptage
    for _ in range(100):  # la durée de vie est reposée plus tard, sans appel de plus à chaque requête
        budget.take()
    assert redis.ttl and redis.expire_calls == 2


@pytest.fixture
def plafond_atteint(monkeypatch):
    monkeypatch.setattr(app_module.AI_BUDGET, "limit", 0)


def _never_called(monkeypatch):
    return install_provider(monkeypatch, error="l'IA ne doit pas être appelée après le plafond")


def test_chat_answers_from_the_verified_base_without_calling_the_ai(plafond_atteint, monkeypatch):
    provider = _never_called(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = post_chat("Parle-moi de l'île de Gorée en détail")
    events = [json.loads(line) for line in finish(response).decode().splitlines() if line.strip()]
    assert response.status_code == 200
    assert provider.calls == []
    assert not any("error" in event for event in events), events
    assert "Île de Gorée" in "".join(event.get("d", "") for event in events)
    assert any(event.get("degraded") for event in events)


def test_chat_json_mode_also_uses_the_base(plafond_atteint, monkeypatch):
    provider = _never_called(monkeypatch)
    response = post_chat("Parle-moi de l'île de Gorée en détail", json_mode=True)
    body = json.loads(finish(response))
    assert response.status_code == 200 and provider.calls == []
    assert body["degraded"] is True and "Île de Gorée" in body["reply"]


def test_ready_answers_do_not_count_and_still_work(plafond_atteint, monkeypatch):
    provider = _never_called(monkeypatch)
    response = post_chat("Combien font 100 euros en FCFA ?")
    text = "".join(json.loads(line).get("d", "") for line in finish(response).decode().splitlines() if line.strip())
    assert "65 595,70 FCFA" in text and provider.calls == []


def test_voice_and_planner_answer_503_with_a_clear_message(plafond_atteint, monkeypatch):
    tts = post_tts(monkeypatch=monkeypatch, error="la voix ne doit pas être appelée après le plafond")
    stt = post_stt(monkeypatch=monkeypatch, error="la dictée ne doit pas être appelée après le plafond")
    trip = app_module.app.test_client().post(
        "/api/trip-planner", json={"arrival": "2026-11-10", "departure": "2026-11-12"},
        headers={"Origin": B}, base_url=B, environ_base={"REMOTE_ADDR": next_ip()},
    )
    for response in (tts, stt, trip):
        assert response.status_code == 503, (response.status_code, response.get_data(as_text=True))
        assert "limite du jour" in response.get_json()["error"]
        assert int(response.headers["Retry-After"]) > 0


def test_below_the_limit_nothing_changes(monkeypatch):
    install_provider(monkeypatch, full_reply=None)
    assert app_module.AI_BUDGET.limit == daily_limit()
    response = post_chat("Parle-moi de l'île de Gorée en détail")
    finish(response)
    assert response.status_code == 200
