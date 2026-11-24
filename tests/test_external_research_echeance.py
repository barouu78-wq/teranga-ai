"""Recherche externe : échéance et parallélisme (aucun appel réseau, fournisseurs simulés).

La recherche s'exécute AVANT le premier mot de la réponse : un fournisseur lent ou en panne ne doit
jamais la retarder au-delà de l'échéance. Les marges des tests sont larges (échéance simulée de
0,6 s, fournisseur « bloqué » 4 s, assertion à 2 s) pour rester stables sur une machine chargée.
"""
from __future__ import annotations

import threading
import time

import pytest

from services import external_research as research


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _only_keys(monkeypatch, *providers):
    """Seules les clés des fournisseurs donnés sont configurées (valeurs factices)."""
    for name in ("TAVILY", "EXA", "FIRECRAWL"):
        monkeypatch.delenv(f"{name}_API_KEY", raising=False)
    for name in providers:
        monkeypatch.setenv(f"{name.upper()}_API_KEY", "test-key")


def _tavily_data(text="Résultat Tavily."):
    return {"results": [{"title": "Source Tavily", "url": "https://example.org/t", "content": text}]}


def _exa_data(text="Résultat Exa."):
    return {"results": [{"title": "Source Exa", "url": "https://example.org/e", "text": text}]}


@pytest.fixture
def hang():
    """Simule un fournisseur qui ne répond pas : bloque jusqu'à 4 s, libéré à la fin du test."""
    release = threading.Event()

    def block():
        release.wait(4.0)

    yield block
    release.set()


def _timed(function, *args):
    started = time.perf_counter()
    result = function(*args)
    return result, time.perf_counter() - started


def test_slow_provider_does_not_delay_the_answer_and_the_fast_one_is_kept(monkeypatch, hang):
    _only_keys(monkeypatch, "tavily", "exa")
    monkeypatch.setattr(research, "DEADLINE_S", 0.6, raising=False)

    def slow_tavily(query, max_results=5):
        hang()
        return _tavily_data()

    monkeypatch.setattr(research, "search_tavily", slow_tavily)
    monkeypatch.setattr(research, "search_exa", lambda query, num_results=5: _exa_data())
    result, elapsed = _timed(research.search_context, "emploi Sénégal")
    assert result is not None and result["provider"] == "exa"
    assert elapsed < 2.0, f"la réponse a attendu le fournisseur lent ({elapsed:.1f} s)"


def test_when_every_provider_hangs_the_answer_stops_at_the_deadline(monkeypatch, hang):
    _only_keys(monkeypatch, "tavily", "exa", "firecrawl")
    monkeypatch.setattr(research, "DEADLINE_S", 0.6, raising=False)

    def slow(*args, **kwargs):
        hang()
        return _tavily_data()

    monkeypatch.setattr(research, "search_tavily", slow)
    monkeypatch.setattr(research, "search_exa", slow)
    monkeypatch.setattr(research, "scrape_firecrawl", slow)
    result, elapsed = _timed(research.search_context, "Analyse https://exemple.org/page")
    assert result is None
    assert elapsed < 2.0, f"l'échéance n'a pas coupé l'attente ({elapsed:.1f} s)"


def test_search_results_back_in_time_are_kept_when_firecrawl_hangs(monkeypatch, hang):
    _only_keys(monkeypatch, "tavily", "firecrawl")
    monkeypatch.setattr(research, "DEADLINE_S", 0.6, raising=False)

    def slow_firecrawl(url):
        hang()
        return {"data": {"markdown": "Page lente."}}

    monkeypatch.setattr(research, "scrape_firecrawl", slow_firecrawl)
    monkeypatch.setattr(research, "search_tavily", lambda query, max_results=5: _tavily_data())
    result, elapsed = _timed(research.search_context, "Résume https://exemple.org/page")
    assert result is not None and result["provider"] == "tavily"
    assert elapsed < 2.0, f"Firecrawl a retardé la réponse ({elapsed:.1f} s)"


def test_providers_run_in_parallel(monkeypatch):
    _only_keys(monkeypatch, "tavily", "exa")
    barrier = threading.Barrier(2)
    met = []

    def rendezvous(data):
        # Les deux appels doivent être en cours en même temps pour franchir la barrière.
        try:
            barrier.wait(timeout=2.0)
            met.append(True)
        except threading.BrokenBarrierError:
            met.append(False)
        return data

    monkeypatch.setattr(research, "search_tavily", lambda query, max_results=5: rendezvous(_tavily_data()))
    monkeypatch.setattr(research, "search_exa", lambda query, num_results=5: rendezvous(_exa_data()))
    assert research.search_context("emploi Sénégal") is not None
    stop = time.monotonic() + 4.0
    while len(met) < 2 and time.monotonic() < stop:
        time.sleep(0.01)
    assert met == [True, True], "les fournisseurs ne tournent pas en parallèle"


def test_firecrawl_keeps_priority_for_an_explicit_url_even_when_slower(monkeypatch):
    _only_keys(monkeypatch, "tavily", "exa", "firecrawl")

    def slow_firecrawl(url):
        time.sleep(0.3)
        return {"data": {"markdown": "Contenu de la page.", "metadata": {"title": "Page"}}}

    monkeypatch.setattr(research, "scrape_firecrawl", slow_firecrawl)
    monkeypatch.setattr(research, "search_tavily", lambda query, max_results=5: _tavily_data())
    monkeypatch.setattr(research, "search_exa", lambda query, num_results=5: _exa_data())
    result = research.search_context("Résume https://exemple.org/page")
    assert result["provider"] == "firecrawl"
    assert "Contenu de la page." in result["context"]


def test_failed_firecrawl_falls_back_to_search_and_each_provider_is_called_once(monkeypatch):
    _only_keys(monkeypatch, "tavily", "exa", "firecrawl")
    calls = []

    def failing_firecrawl(url):
        calls.append("firecrawl")
        raise research.ProviderRequestError("403")

    def failing_tavily(query, max_results=5):
        calls.append("tavily")
        raise research.ProviderRequestError("offline")

    def exa(query, num_results=5):
        calls.append("exa")
        return _exa_data()

    monkeypatch.setattr(research, "scrape_firecrawl", failing_firecrawl)
    monkeypatch.setattr(research, "search_tavily", failing_tavily)
    monkeypatch.setattr(research, "search_exa", exa)
    result = research.search_context("Résume https://exemple.org/page")
    assert result["provider"] == "exa"
    assert sorted(calls) == ["exa", "firecrawl", "tavily"]


def test_unexpected_provider_crash_is_ignored(monkeypatch):
    _only_keys(monkeypatch, "tavily", "exa")

    def crashing(query, max_results=5):
        raise RuntimeError("bug inattendu du fournisseur")

    monkeypatch.setattr(research, "search_tavily", crashing)
    monkeypatch.setattr(research, "search_exa", lambda query, num_results=5: _exa_data())
    assert research.search_context("emploi Sénégal")["provider"] == "exa"


def test_without_any_key_nothing_runs_and_no_call_is_made(monkeypatch):
    _only_keys(monkeypatch)
    calls = []
    for name in ("search_tavily", "search_exa", "scrape_firecrawl"):
        monkeypatch.setattr(research, name, lambda *a, _n=name, **k: calls.append(_n))
    monkeypatch.setattr(research.httpx, "post", lambda *a, **k: calls.append("httpx"))
    started = []
    real_start = threading.Thread.start
    monkeypatch.setattr(threading.Thread, "start", lambda self: (started.append(self.name), real_start(self))[1])
    assert research.search_context("Que dit https://exemple.org/page ?") is None
    assert calls == [] and started == []


def test_network_calls_of_the_chat_search_use_a_short_timeout(monkeypatch):
    """Un fil abandonné à l'échéance doit se terminer vite : plus de lecture de 15 s sur le chemin du chat."""
    _only_keys(monkeypatch, "tavily")
    seen = []
    monkeypatch.setattr(
        research.httpx, "post",
        lambda *args, **kwargs: (seen.append(kwargs["timeout"]) or FakeResponse({"results": []})),
    )
    research.search_tavily("restaurants Dakar")
    assert seen[0].read is not None and seen[0].read <= 8.0
    assert seen[0].connect is not None and seen[0].connect <= 5.0
