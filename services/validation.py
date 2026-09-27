"""Input normalization helpers shared by Teranga AI routes."""
from __future__ import annotations

import re
import unicodedata


CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ZERO_WIDTH_CHARS = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


def normalize(value: object) -> str:
    """Return a lowercase, accent-insensitive representation."""
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in value if not unicodedata.combining(ch)).lower().strip()


def sanitize_text(text: object, max_len: int) -> str:
    """Remove control characters and normalize whitespace safely."""
    value = ZERO_WIDTH_CHARS.sub("", CONTROL_CHARS.sub("", str(text or "")))
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()[:max_len]
