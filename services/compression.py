"""Gzip compression of buffered text responses.

The HTML/JS of the home page is ~130 KB and compresses ~3.5x. Streamed
responses (chat NDJSON) are never touched: buffering them would break the
word-by-word display.
"""

from __future__ import annotations

import gzip

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


def gzip_response(response, accept_encoding: str, *, level: int = 6):
    if "gzip" not in (accept_encoding or "").lower():
        return response
    if response.direct_passthrough or response.is_streamed:
        return response
    if response.status_code < 200 or response.status_code >= 300 or response.status_code == 204:
        return response
    if response.headers.get("Content-Encoding") or response.mimetype not in COMPRESSIBLE_TYPES:
        return response
    body = response.get_data()
    if len(body) < MIN_SIZE:
        return response
    response.set_data(gzip.compress(body, compresslevel=level, mtime=0))
    response.headers["Content-Encoding"] = "gzip"
    vary = response.headers.get("Vary", "")
    if "accept-encoding" not in vary.lower():
        response.headers["Vary"] = (vary + ", " if vary else "") + "Accept-Encoding"
    return response
