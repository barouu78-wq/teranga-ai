"""Text normalization helpers for assistant responses."""
from __future__ import annotations

import re

from services.validation import sanitize_text


def clean_answer(text: object) -> str:
    """Normalize assistant output for the plain-text web client."""
    text = sanitize_text(text, 8000)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    text = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```", ""), text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
