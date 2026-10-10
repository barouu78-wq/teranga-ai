"""Claude (Anthropic) : IA de secours, ou IA principale si AI_PRINCIPALE=claude.

Tout est inactif tant que ANTHROPIC_API_KEY n'est pas défini sur l'hébergeur.
- Secours : quand OpenAI ne répond pas, Claude donne quand même une réponse écrite.
- Principale : AI_PRINCIPALE=claude fait passer le chat et le planificateur par
  Claude (avec sa recherche web) ; OpenAI devient alors le secours.
La voix reste toujours sur OpenAI.

Les flux Claude sont traduits en événements au format de l'API Responses
d'OpenAI (`response.output_text.delta`, `response.completed`…) : les routes
existantes les lisent sans savoir quelle IA a répondu.
"""

from __future__ import annotations

import os
import threading
from types import SimpleNamespace
from typing import Any, Iterator

DEFAULT_MODEL = "claude-opus-5-5"
# Re-exécute côté serveur une demande refusée par prudence sur le modèle recommandé.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}
MAX_CONTINUATIONS = 2

_client_lock = threading.Lock()
_clients: dict[str, Any] = {}


def backup_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def claude_is_primary() -> bool:
    """Vrai si AI_PRINCIPALE=claude et que la clé Anthropic est en place."""
    return os.getenv("AI_PRINCIPALE", "openai").strip().lower() == "claude" and backup_enabled()


def claude_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _client():
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    with _client_lock:
        client = _clients.get(key)
        if client is None:
            import anthropic

            # Pas de nouvelle tentative : le secours OpenAI prend le relais plus vite.
            client = anthropic.Anthropic(api_key=key, max_retries=0)
            _clients.clear()
            _clients[key] = client
        return client


def _sources(content) -> list[dict]:
    """Pages citées par la recherche web de Claude (titre + adresse), sans doublon."""
    found, seen = [], set()
    for block in content or []:
        for citation in getattr(block, "citations", None) or []:
            url = str(getattr(citation, "url", "") or "")
            if url.startswith(("http://", "https://")) and url not in seen:
                seen.add(url)
                found.append({"url": url, "title": str(getattr(citation, "title", "") or "")})
    return found[:5]


def _text(content) -> str:
    return "".join(getattr(b, "text", "") or "" for b in content or [] if getattr(b, "type", "") == "text")


def claude_events(
    prompt: str,
    *,
    system: str = "",
    max_tokens: int = 4000,
    timeout: float = 60.0,
    web: bool = False,
    effort: str = "low",
    client: Any = None,
) -> Iterator[SimpleNamespace]:
    """Flux Claude au format des événements OpenAI Responses.

    Lève une exception si Claude échoue ou refuse sans rien écrire : l'appelant
    passe alors au secours.
    """
    client = client or _client()
    messages: list[dict] = [{"role": "user", "content": str(prompt)}]
    params: dict[str, Any] = {
        "model": claude_model(),
        "max_tokens": int(max_tokens),
        "output_config": {"effort": effort},
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
        "timeout": timeout,
    }
    if system:
        params["system"] = str(system)
    if web:
        params["tools"] = [WEB_SEARCH_TOOL]
    parts: list[str] = []
    sources: list[dict] = []
    stop_reason = None
    usage = {"input_tokens": 0, "output_tokens": 0}
    for _ in range(MAX_CONTINUATIONS + 1):
        with client.beta.messages.stream(messages=messages, **params) as stream:
            for text in stream.text_stream:
                if text:
                    parts.append(text)
                    yield SimpleNamespace(type="response.output_text.delta", delta=text)
            message = stream.get_final_message()
        stop_reason = getattr(message, "stop_reason", None)
        for name in usage:
            usage[name] += int(getattr(getattr(message, "usage", None), name, 0) or 0)
        sources = (sources + [s for s in _sources(message.content) if s not in sources])[:5]
        if stop_reason != "pause_turn":
            break
        # La recherche web a atteint sa limite d'étapes : on relance pour finir la réponse.
        messages = messages + [{"role": "assistant", "content": message.content}]
    if stop_reason == "refusal" and not parts:
        raise RuntimeError("Claude refusal")
    text = "".join(parts)
    kind = "response.incomplete" if stop_reason == "max_tokens" else "response.completed"
    status = "incomplete" if kind == "response.incomplete" else "completed"
    yield SimpleNamespace(type=kind, response=SimpleNamespace(output_text=text, sources=sources, usage=SimpleNamespace(**usage), status=status))


def claude_response(prompt: str, **kwargs) -> SimpleNamespace:
    """Réponse complète (objet avec output_text et sources), comme responses.create."""
    final = SimpleNamespace(output_text="", sources=[], usage=None)
    for event in claude_events(prompt, **kwargs):
        if event.type in ("response.completed", "response.incomplete"):
            final = event.response
    return final


def backup_complete(
    prompt: str,
    *,
    system: str = "",
    max_tokens: int = 2000,
    timeout: float = 60.0,
    client: Any = None,
) -> str:
    """Texte de la réponse de Claude, ou "" si Claude n'est pas configuré."""
    if not backup_enabled() or not str(prompt or "").strip():
        return ""
    return claude_response(prompt, system=system, max_tokens=max_tokens, timeout=timeout, client=client).output_text.strip()
