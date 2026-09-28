"""BCEAO foreign-exchange rate retrieval and caching."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from urllib.request import Request, urlopen

FX_SOURCE_URL = "https://www.bceao.int/fr/cours/cours-de-reference-des-principales-devises-contre-Franc-CFA"
FX_CACHE_TTL = 300
DEFAULT_RATES = {"EUR": 655.957, "USD": 577.070, "GBP": 762.860}


def _clean_html_cell(value: object) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def parse_bceao_rates(raw: str, fallback: dict[str, float]) -> tuple[str, dict[str, float]]:
    cells = re.findall(r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", raw, re.I | re.S)
    normalized = [_clean_html_cell(cell) for cell in cells]
    aliases = {
        "EUR": {"euro"},
        "USD": {"dollar us", "dollar américain", "dollar americain"},
        "GBP": {"livre sterling"},
    }
    rates = dict(fallback)
    for index, cell in enumerate(normalized):
        key = cell.casefold()
        for code, names in aliases.items():
            if key in names and index + 1 < len(normalized):
                raw_value = normalized[index + 1].replace(" ", "").replace(",", ".")
                try:
                    value = float(raw_value)
                except ValueError:
                    continue
                if value > 0:
                    rates[code] = value
    date_match = re.search(r"Cours des devises du\s+([^<\r\n]+)", raw, re.I)
    return (date_match.group(1).strip() if date_match else ""), rates


def fetch_bceao_rates(
    cache: dict[str, object],
    *,
    now: float | None = None,
    fetch: Callable[..., object] | None = None,
    logger: object | None = None,
) -> dict[str, object]:
    now = time.time() if now is None else now
    if now - float(cache["at"]) < FX_CACHE_TTL:
        return cache
    try:
        requester = fetch or urlopen
        req = Request(FX_SOURCE_URL, headers={"User-Agent": "TerangaAI/1.0"})
        response = requester(req, timeout=5)
        try:
            raw = response.read().decode("utf-8", "ignore")
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
        date, rates = parse_bceao_rates(raw, dict(cache["rates"]))
        cache = {"at": now, "date": date, "rates": rates}
        return cache
    except Exception:
        if logger is not None:
            logger.warning("Rafraîchissement BCEAO indisponible; conservation du dernier cours valide.")
        return cache
