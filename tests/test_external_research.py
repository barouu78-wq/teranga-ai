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


def test_search_context_uses_firecrawl_for_explicit_url(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.setattr(
        research, "scrape_firecrawl",
        lambda url: {"data": {"markdown": "# Teranga AI\nContenu du site.", "metadata": {"title": "Teranga AI"}}},
    )
    result = research.search_context("Analyse ce site https://teranga-ai.fr/")
    assert result["provider"] == "firecrawl"
    assert "Contenu du site." in result["context"]
    assert result["sources"] == [{"title": "Teranga AI", "url": "https://teranga-ai.fr/"}]

def test_search_console_refreshes_oauth_token_and_queries_property(monkeypatch):
    monkeypatch.delenv("GOOGLE_SEARCH_CONSOLE_TOKEN", raising=False)
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN", "refresh-test")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_CLIENT_ID", "client-test")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_CLIENT_SECRET", "secret-test")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:teranga-ai.fr")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if "oauth2.googleapis.com" in url:
            return FakeResponse({"access_token": "access-test"})
        return FakeResponse({"rows": [{"keys": ["teranga-ai.fr"], "clicks": 4}]})

    monkeypatch.setattr(research.httpx, "post", fake_post)
    result = research.google_search_console_query(
        start_date="2026-10-01", end_date="2026-10-07", dimensions=["query"]
    )
    assert result["rows"][0]["clicks"] == 4
    assert calls[0][1]["data"]["grant_type"] == "refresh_token"
    assert calls[1][1]["headers"]["Authorization"] == "Bearer access-test"
    assert calls[1][1]["json"]["dimensions"] == ["query"]


def test_search_console_rejects_unknown_dimensions(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_TOKEN", "access-test")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:teranga-ai.fr")
    with pytest.raises(ValueError):
        research.google_search_console_query(
            start_date="2026-10-01", end_date="2026-10-07", dimensions=["secretDimension"]
        )


def test_semrush_parses_csv_without_exposing_api_key(monkeypatch):
    monkeypatch.setenv("SEMRUSH_API_KEY", "semrush-test")
    calls = []

    class CsvResponse(FakeResponse):
        text = "Ph;Po;Nq;Cp;Ur\nassistant Sénégal;3;100;0.2;https://teranga-ai.fr/"

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return CsvResponse({})

    monkeypatch.setattr(research.httpx, "get", fake_get)
    rows = research.semrush_domain_organic("teranga-ai.fr", display_limit=500)
    assert rows[0]["Ph"] == "assistant Sénégal"
    assert calls[0][1]["params"]["display_limit"] == "100"
    assert calls[0][1]["params"]["key"] == "semrush-test"


def test_semrush_rejects_invalid_domain(monkeypatch):
    monkeypatch.setenv("SEMRUSH_API_KEY", "semrush-test")
    with pytest.raises(ValueError):
        research.semrush_domain_organic("https://teranga-ai.fr/path")

