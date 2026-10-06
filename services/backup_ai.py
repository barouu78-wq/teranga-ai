"""IA de secours (Claude d'Anthropic) quand OpenAI ne répond pas.

Activée seulement si ANTHROPIC_API_KEY est défini sur l'hébergeur. Appel HTTP
direct (httpx, déjà utilisé par le projet) : aucune dépendance de plus. Pas de
recherche web ni de voix ici : le secours sert à toujours donner une réponse
écrite (chat et planificateur) pendant une panne d'OpenAI.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5-5"


def backup_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def backup_complete(
    prompt: str,
    *,
    system: str = "",
    max_tokens: int = 2000,
    timeout: float = 60.0,
    http_post: Any = None,
) -> str:
    """Texte de la réponse de Claude, ou "" si le secours est absent ou en échec."""
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key or not str(prompt or "").strip():
        return ""
    body: dict[str, Any] = {
        "model": os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "max_tokens": int(max_tokens),
        "messages": [{"role": "user", "content": str(prompt)}],
    }
    if system:
        body["system"] = str(system)
    headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
    post = http_post or httpx.post
    response = post(API_URL, json=body, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    parts = [block.get("text", "") for block in data.get("content", []) if isinstance(block, dict) and block.get("type") == "text"]
    return "".join(parts).strip()
