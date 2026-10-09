"""Connecteurs facultatifs de recherche externe pour Teranga AI.

Aucun appel réseau n'est effectué à l'import. Les clés sont lues depuis
l'environnement et ne doivent jamais être journalisées ni exposées au navigateur.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx


TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class ProviderNotConfigured(RuntimeError):
    """Le fournisseur demandé ne dispose pas d'une clé API."""


class ProviderRequestError(RuntimeError):
    """Le fournisseur a refusé la requête ou renvoyé une réponse invalide."""


def configured_providers() -> dict[str, bool]:
    """Indique uniquement si les variables de configuration existent."""
    return {
        "tavily": bool(os.getenv("TAVILY_API_KEY", "").strip()),
        "exa": bool(os.getenv("EXA_API_KEY", "").strip()),
        "firecrawl": bool(os.getenv("FIRECRAWL_API_KEY", "").strip()),
        "semrush": bool(os.getenv("SEMRUSH_API_KEY", "").strip()),
        "google_search_console": bool(
            os.getenv("GOOGLE_SEARCH_CONSOLE_CREDENTIALS", "").strip()
            or os.getenv("GOOGLE_SEARCH_CONSOLE_TOKEN", "").strip()
        ),
    }


def _key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ProviderNotConfigured(f"Le fournisseur {name} n'est pas configuré.")
    return value


def _json_post(
    url: str, *, headers: dict[str, str], payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        # Ne pas propager le corps de réponse ni les en-têtes qui peuvent contenir des secrets.
        raise ProviderRequestError("Échec de la requête au fournisseur externe.") from exc
    if not isinstance(data, dict):
        raise ProviderRequestError("Réponse invalide du fournisseur externe.")
    return data


def search_tavily(query: str, *, max_results: int = 5) -> dict[str, Any]:
    """Recherche web avec Tavily."""
    query = query.strip()
    if not query:
        raise ValueError("La requête de recherche est obligatoire.")
    return _json_post(
        "https://api.tavily.com/search",
        headers={"Content-Type": "application/json"},
        payload={
            "api_key": _key("TAVILY_API_KEY"),
            "query": query,
            "search_depth": "basic",
            "max_results": max(1, min(int(max_results), 10)),
            "include_answer": False,
        },
    )


def search_exa(query: str, *, num_results: int = 5) -> dict[str, Any]:
    """Recherche sémantique avec Exa."""
    query = query.strip()
    if not query:
        raise ValueError("La requête de recherche est obligatoire.")
    return _json_post(
        "https://api.exa.ai/search",
        headers={
            "x-api-key": _key("EXA_API_KEY"),
            "Content-Type": "application/json",
        },
        payload={
            "query": query,
            "type": "auto",
            "numResults": max(1, min(int(num_results), 10)),
            "contents": {"text": {"maxCharacters": 2000}},
        },
    )


def scrape_firecrawl(url: str) -> dict[str, Any]:
    """Extrait le contenu lisible d'une URL publique via Firecrawl."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Une URL publique HTTP(S) valide est obligatoire.")
    return _json_post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={
            "Authorization": f"Bearer {_key('FIRECRAWL_API_KEY')}",
            "Content-Type": "application/json",
        },
        payload={"url": url.strip(), "formats": ["markdown"]},
    )
