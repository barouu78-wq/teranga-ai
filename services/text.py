"""Text normalization helpers for assistant responses."""
from __future__ import annotations

import re

from services.validation import sanitize_text


def clean_answer(text: object) -> str:
    """Normalize assistant output for the plain-text web client."""
    text = sanitize_text(text, 8000)
    # Les adresses web sont mises de côté : « Île_de_Gorée » ne doit pas perdre ses « _ ».
    urls: list[str] = []

    def _keep_url(match: re.Match) -> str:
        urls.append(match.group(0))
        return f"\x00{len(urls) - 1}\x00"

    text = re.sub(r"https?://[^\s<>()\[\]]+", _keep_url, text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    text = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```", ""), text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    # Un « * » n'ouvre une emphase que s'il est collé au mot qui suit (et ne la ferme que s'il est
    # collé au mot qui précède) : « 2 adultes * 3 nuits * 45 000 » garde ses signes de multiplication.
    text = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"\1", text)
    # Un « _ » au milieu d'un mot (@nom_de_compte, ma_liste.pdf) n'est pas de l'italique.
    text = re.sub(r"(?<!\w)_(?![\s_])(.+?)(?<![\s_])_(?!\w)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    # Listes : « - » ou « * » deviennent « • » (plus lisible que des lignes nues ; la voix les ignore).
    text = re.sub(r"(?m)^\s*[-*•]\s+", "• ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: urls[int(m.group(1))], text)
    return text.strip()


def fold_text(text: object) -> str:
    """Minuscules sans accents, tirets et apostrophes changés en espaces (« Aïd-el-Kébir » → « aid el kebir »)."""
    import unicodedata

    raw = unicodedata.normalize("NFD", str(text or "").casefold())
    plain = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(plain.replace("-", " ").replace("'", " ").replace("’", " ").split())
