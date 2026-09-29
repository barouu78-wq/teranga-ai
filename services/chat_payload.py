"""Chat payload normalization helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Callable


def normalize_chat_input(
    data: object,
    *,
    sanitize: Callable[[object, int], str],
    max_message_length: int,
    max_history_items: int,
    max_history_item_length: int,
    safe_languages: Iterable[str],
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(data, Mapping):
        return None, "invalid"

    message = sanitize(data.get("message", ""), max_message_length)
    history = data.get("history", [])
    language = str(data.get("language", "fr")).lower()[:8]
    if language not in set(safe_languages):
        language = "fr"

    if not isinstance(history, list):
        history = []
    normalized_history = [
        {
            "role": str(item.get("role", "")).lower(),
            "content": sanitize(item.get("content", ""), max_history_item_length),
        }
        for item in history[-max_history_items:]
        if isinstance(item, Mapping)
        and str(item.get("role", "")).lower() in {"user", "assistant"}
    ]

    audience = str(data.get("audience", "tourist")).lower()[:16]
    if audience not in {"tourist", "resident", "diaspora", "merchant"}:
        audience = "tourist"

    context_place = sanitize(data.get("context_place", ""), 120).strip()
    trip_context = sanitize(data.get("trip_context", ""), 1600).strip()
    trip_edit_request = sanitize(data.get("trip_edit_request", ""), 500).strip()

    if not message:
        return None, "empty"

    return {
        "message": message,
        "history": normalized_history,
        "language": language,
        "audience": audience,
        "context_place": context_place,
        "trip_context": trip_context,
        "trip_edit_request": trip_edit_request,
    }, None
