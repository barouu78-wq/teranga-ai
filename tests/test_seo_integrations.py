"""Tests sans réseau des intégrations SEO."""
from __future__ import annotations

import pytest

from services import seo_integrations as seo


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self.payload = payload
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_search_console_uses_access_token_and_limits_rows(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_TOKEN", "temporary-token")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:teranga-ai.fr")
    calls = []
    monkeypatch.setattr(
        seo.httpx, "post",
        lambda *args, **kwargs: (calls.append((args, kwargs)) or FakeResponse({"rows": []})),
    )
    result = seo.search_console_query(start_date="2026-09-01", end_date="2026-09-30", row_limit=99999)
    assert result == {"rows": []}
    assert calls[0][1]["headers"]["Authorization"] == "Bearer temporary-token"
    assert calls[0][1]["json"]["rowLimit"] == 25000
    assert "sc-domain%3Ateranga-ai.fr" in calls[0][0][0]


def test_search_console_rejects_invalid_dimensions(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_TOKEN", "temporary-token")
    monkeypatch.setenv("GOOGLE_SEARCH_CONSOLE_SITE_URL", "sc-domain:teranga-ai.fr")
    with pytest.raises(ValueError):
        seo.search_console_query(dimensions=["password"])


def test_semrush_domain_overview_parses_csv(monkeypatch):
    monkeypatch.setenv("SEMRUSH_API_KEY", "private-key")
    calls = []
    monkeypatch.setattr(
        seo.httpx, "get",
        lambda *args, **kwargs: (calls.append((args, kwargs)) or FakeResponse(text="Database;Domain;Rank;Organic Keywords\nfr;teranga-ai.fr;100;23")),
    )
    result = seo.semrush_domain_overview("https://teranga-ai.fr/", max_rows=99)
    assert result["domain"] == "teranga-ai.fr"
    assert result["rows"][0]["Organic Keywords"] == "23"
    assert calls[0][1]["params"]["key"] == "private-key"
    assert result["rows"][0]["Domain"] == "teranga-ai.fr"


def test_semrush_requires_api_key(monkeypatch):
    monkeypatch.delenv("SEMRUSH_API_KEY", raising=False)
    with pytest.raises(seo.SeoIntegrationError):
        seo.semrush_domain_overview("teranga-ai.fr")


def test_search_console_requires_authentication(monkeypatch):
    monkeypatch.delenv("GOOGLE_SEARCH_CONSOLE_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN", raising=False)
    with pytest.raises(seo.SeoIntegrationError):
        seo.search_console_query()
