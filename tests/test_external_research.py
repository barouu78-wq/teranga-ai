"""Tests sans réseau des connecteurs de recherche externe."""
from __future__ import annotations

import pytest

from services import external_research as research


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_configured_providers_only_reports_presence(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "secret")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    result = research.configured_providers()
    assert result["tavily"] is True
    assert result["exa"] is False
    assert set(result) == {
        "tavily", "exa", "firecrawl", "semrush", "google_search_console"
    }
    assert "secret" not in repr(result)


def test_tavily_search_clamps_result_count(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(
        research.httpx, "post",
        lambda *args, **kwargs: (calls.append((args, kwargs)) or FakeResponse({"results": []})),
    )
    assert research.search_tavily("restaurants Dakar", max_results=99) == {"results": []}
    assert calls[0][0][0] == "https://api.tavily.com/search"
    assert calls[0][1]["json"]["max_results"] == 10
    assert calls[0][1]["json"]["query"] == "restaurants Dakar"


def test_exa_requires_nonempty_query(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    with pytest.raises(ValueError):
        research.search_exa("   ")


def test_missing_provider_key_is_clear(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    with pytest.raises(research.ProviderNotConfigured):
        research.scrape_firecrawl("https://example.com")


@pytest.mark.parametrize("url", ["", "file:///etc/passwd", "javascript:alert(1)", "//example.com"])
def test_firecrawl_rejects_non_http_urls(monkeypatch, url):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    with pytest.raises(ValueError):
        research.scrape_firecrawl(url)


def test_firecrawl_sends_bearer_auth(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(
        research.httpx, "post",
        lambda *args, **kwargs: (calls.append((args, kwargs)) or FakeResponse({"success": True})),
    )
    assert research.scrape_firecrawl("https://example.com/page") == {"success": True}
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0][1]["json"]["formats"] == ["markdown"]


def test_search_context_uses_tavily_and_returns_http_sources(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.setattr(
        research, "search_tavily",
        lambda query, max_results=5: {"results": [
            {"title": "Guide Dakar", "url": "https://example.org/dakar", "content": "Informations pratiques."},
            {"title": "URL invalide", "url": "javascript:alert(1)", "content": "À ignorer."},
        ]},
    )
    result = research.search_context("visiter Dakar")
    assert result["provider"] == "tavily"
    assert "Informations pratiques." in result["context"]
    assert len(result["sources"]) == 1
    assert result["sources"][0]["url"] == "https://example.org/dakar"


def test_search_context_falls_back_to_exa_when_tavily_fails(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setattr(
        research, "search_tavily",
        lambda query, max_results=5: (_ for _ in ()).throw(research.ProviderRequestError("offline")),
    )
    monkeypatch.setattr(
        research, "search_exa",
        lambda query, num_results=5: {"results": [
            {"title": "Source Exa", "url": "https://example.org", "text": "Texte extrait."},
        ]},
    )
    result = research.search_context("emploi Sénégal")
    assert result["provider"] == "exa"
    assert "Texte extrait." in result["context"]


def test_search_context_without_keys_is_disabled(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    assert research.search_context("question") is None
