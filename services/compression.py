"""Gzip compression of buffered text responses.

The HTML/JS of the home page is ~130 KB and compresses ~3.5x. Streamed
responses (chat NDJSON) are never touched: buffering them would break the
word-by-word display.
"""

from __future__ import annotations

import gzip
from collections import OrderedDict

# Fichiers statiques déjà compressés, par (chemin, ETag) : home.js (95 Ko)
# n'est compressé qu'une fois par version et par worker.
_STATIC_CACHE: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_STATIC_CACHE_MAX = 32

COMPRESSIBLE_TYPES = frozenset({
    "text/html",
    "text/css",
    "text/plain",
    "text/javascript",
    "application/javascript",
    "application/json",
    "application/xml",
    "application/manifest+json",
    "image/svg+xml",
})
MIN_SIZE = 1024


def gzip_response(response, accept_encoding: str, *, level: int = 6, static_path: str = ""):
    if "gzip" not in (accept_encoding or "").lower():
        return response
    if response.status_code != 200 and not (200 < response.status_code < 300 and response.status_code not in (204, 206)):
        return response
    if response.headers.get("Content-Encoding") or response.mimetype not in COMPRESSIBLE_TYPES:
        return response
    cache_key = None
    if response.direct_passthrough:
        # Fichier envoyé par send_file (/static/) : lu une fois puis mis en cache.
        if not static_path or response.status_code != 200:
            return response
        cache_key = (static_path, response.headers.get("ETag", ""))
        cached = _STATIC_CACHE.get(cache_key)
        if cached is not None:
            _STATIC_CACHE.move_to_end(cache_key)
            response.direct_passthrough = False
            response.set_data(cached)
            return _mark_gzip(response)
        response.direct_passthrough = False
    elif response.is_streamed:
        return response
    body = response.get_data()
    if len(body) < MIN_SIZE:
        return response
    compressed = gzip.compress(body, compresslevel=level, mtime=0)
    if cache_key is not None:
        _STATIC_CACHE[cache_key] = compressed
        while len(_STATIC_CACHE) > _STATIC_CACHE_MAX:
            _STATIC_CACHE.popitem(last=False)
    response.set_data(compressed)
    return _mark_gzip(response)


def _mark_gzip(response):
    response.headers["Content-Encoding"] = "gzip"
    if response.headers.get("ETag", "").startswith('"'):
        # Contenu différent de l'original : ETag faible pour rester honnête.
        response.headers["ETag"] = "W/" + response.headers["ETag"]
    vary = response.headers.get("Vary", "")
    if "accept-encoding" not in vary.lower():
        response.headers["Vary"] = (vary + ", " if vary else "") + "Accept-Encoding"
    return response
