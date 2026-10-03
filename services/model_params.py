"""OpenAI response parameter construction for Teranga AI."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


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
        "max_output_tokens": 520 if (use_web or planner) else 320,
        "reasoning": {"effort": effort},
        "truncation": "auto",
        "stream": stream,
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
