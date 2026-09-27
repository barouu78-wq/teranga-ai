"""Conversation formatting helpers for Teranga AI."""

from __future__ import annotations

from collections.abc import Sequence

from .validation import sanitize_text


def build_conversation(
    history: Sequence[dict] | None,
    message: str,
    *,
    max_history_items: int,
    max_history_item_length: int,
    max_history_chars: int,
) -> str:
    lines = []
    if isinstance(history, (list, tuple)):
        recent = history[-max_history_items:]
        for index, item in enumerate(recent):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).lower()
            content = sanitize_text(item.get("content", ""), max_history_item_length)
            if role not in {"user", "assistant"} or not content:
                continue
            if index == len(recent) - 1 and role == "user" and content == message:
                continue
            label = "Utilisateur" if role == "user" else "Teranga AI"
            lines.append(f"{label}: {content}")
    conversation = "\n".join(lines)
    return (
        "<historique_non_fiable>\n"
        + conversation
        + "\n</historique_non_fiable>\n"
        + "<demande_utilisateur>\n"
        + message
        + "\n</demande_utilisateur>"
    )[-max_history_chars:]
