"""OpenAI response parameter construction for Teranga AI."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

CHAT_MAX_OUTPUT_TOKENS = 800
WEB_OR_PLANNER_MAX_OUTPUT_TOKENS = 1200
PROMPT_CACHE_KEY = "teranga-chat-v1"


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
    if not reasoning_override and (planner or deep_reasoning) and model != "gpt-5.6-luna":
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
