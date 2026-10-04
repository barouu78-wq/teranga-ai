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
    head = "<historique_non_fiable>\n"
    tail = "\n</historique_non_fiable>\n<demande_utilisateur>\n" + message + "\n</demande_utilisateur>"
    # Au-delà du budget, on retire les tours les plus anciens : la structure
    # (balises, demande actuelle) reste toujours intacte.
    budget = max_history_chars - len(head) - len(tail)
    kept: list[str] = []
    used = 0
    for line in reversed(lines):
        cost = len(line) + (1 if kept else 0)
        if used + cost > budget:
            break
        kept.append(line)
        used += cost
    kept.reverse()
    result = head + "\n".join(kept) + tail
    if len(result) > max_history_chars:
        # Demande seule plus longue que le budget : on garde sa fin, balises comprises.
        result = head + tail[-max(0, max_history_chars - len(head)):]
    return result
