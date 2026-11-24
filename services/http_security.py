"""HTTP origin validation helpers.

Pure helpers for validating browser Origin/Referer values against the
application allowlist.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse


def origin_allowed(
    origin: object,
    referer: object,
    allowed_origins: Iterable[str],
) -> bool:
    allowed = set(allowed_origins)
    if not allowed:
        return True
    origin = str(origin or "")
    referer = str(referer or "")
    if origin:
        return origin in allowed
    if not referer:
        return False
    try:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return False
    return referer_origin in allowed


def json_body(req):
    """Corps JSON de la requête, ou None s'il est absent, invalide ou trop imbriqué.

    `get_json(silent=True)` n'attrape pas RecursionError : un JSON très imbriqué (« [[[[… ») donnait une
    erreur 500 et une trace dans les journaux (audit V3, P2-2). `require_json_post` fait la même chose.
    """
    try:
        return req.get_json(silent=True)
    except RecursionError:
        return None
