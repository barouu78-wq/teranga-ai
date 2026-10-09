"""OpenAI response parameter construction for Teranga AI."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterable
from typing import Any

CHAT_MAX_OUTPUT_TOKENS = 800
WEB_OR_PLANNER_MAX_OUTPUT_TOKENS = 1200
PROMPT_CACHE_KEY = "teranga-chat-v1"

# Noms des modèles OpenAI par défaut. Chacun se règle par une variable d'environnement
# (comme ANTHROPIC_MODEL pour Claude, voir backup_ai.py) ; une valeur vide ou invalide
# retombe sur le défaut. Dans services/, ces deux constantes sont le seul endroit où les
# noms sont écrits (un test le vérifie).
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"  # OPENAI_MODEL : modèle rapide du chat
DEFAULT_OPENAI_COMPLEX_MODEL = "gpt-5.6-sol"  # OPENAI_COMPLEX_MODEL : planification, raisonnement approfondi

# Identifiant plausible : lettres, chiffres et « . _ : / - », sans espace ni caractère de contrôle.
_MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}")


def clean_model_name(value: Any, default: str = "") -> str:
    """Nom de modèle sans espaces superflus ; vide ou invalide, ``default``."""
    name = value.strip() if isinstance(value, str) else ""
    return name if _MODEL_NAME.fullmatch(name) else default


def env_model(name: str, default: str = "") -> str:
    """Nom de modèle lu dans la variable d'environnement ``name`` (lecture à chaque appel)."""
    return clean_model_name(os.getenv(name), default)


def openai_model() -> str:
    """Modèle rapide du chat (OPENAI_MODEL)."""
    return env_model("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def openai_complex_model() -> str:
    """Modèle des demandes de planification ou de raisonnement approfondi (OPENAI_COMPLEX_MODEL)."""
    return env_model("OPENAI_COMPLEX_MODEL", DEFAULT_OPENAI_COMPLEX_MODEL)


def openai_trip_model() -> str:
    """Modèle dédié au planificateur de voyage (OPENAI_TRIP_MODEL) ; chaîne vide s'il n'y en a pas."""
    return env_model("OPENAI_TRIP_MODEL")


def build_model_kwargs(
    payload: dict[str, Any],
    *,
    model: str,
    reasoning_effort: Callable[[bool, bool], str],
    search_context_size: Callable[[str, bool], str],
    preferred_domains: Callable[[str], Iterable[str]],
    stream: bool,
    reasoning_override: str | None = None,
) -> dict[str, Any]:
    use_web = bool(payload["use_web"])
    planner = bool(payload.get("planner"))
    deep_reasoning = bool(payload.get("deep_reasoning"))
    domain = str((payload.get("intent_context") or {}).get("domain") or "general")

    effort = reasoning_override or reasoning_effort(use_web, planner)
    if not reasoning_override and (planner or deep_reasoning) and model != openai_model():
        effort = "medium"

    kwargs: dict[str, Any] = {
        "model": model,
        "instructions": payload["instructions"],
        "input": payload["input_text"],
        # Les tokens de raisonnement sont décomptés de max_output_tokens : une
        # limite trop basse tronque la réponse visible. La longueur effective
        # reste pilotée par les consignes du prompt.
        "max_output_tokens": WEB_OR_PLANNER_MAX_OUTPUT_TOKENS if (use_web or planner) else CHAT_MAX_OUTPUT_TOKENS,
        "reasoning": {"effort": effort},
        "truncation": "auto",
        "stream": stream,
        # Préfixe stable (prompt système) : améliore le taux de cache côté OpenAI,
        # donc la latence du premier token et le coût.
        "prompt_cache_key": PROMPT_CACHE_KEY,
    }
    if use_web:
        tool: dict[str, Any] = {
            "type": "web_search",
            "search_context_size": search_context_size(domain, planner),
        }
        domains = preferred_domains(domain)
        if domains:
            tool["filters"] = {"allowed_domains": list(domains)}
        kwargs["tools"] = [tool]
    return kwargs
