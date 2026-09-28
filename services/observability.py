"""Small, privacy-conscious HTTP observability helpers."""
from __future__ import annotations

import re

_REQUEST_ID_RE = re.compile(r"[^a-zA-Z0-9_-]")


def build_request_log(
    *,
    request_id: object,
    method: object,
    path: object,
    status: object,
    duration_ms: object,
) -> dict[str, object]:
    """Build safe structured request metadata without query strings or bodies."""
    safe_id = _REQUEST_ID_RE.sub("", str(request_id or ""))[:64]
    safe_method = str(method or "")[:12].upper()
    safe_path = str(path or "/").split("?", 1)[0][:200]
    try:
        safe_status = int(status)
    except (TypeError, ValueError):
        safe_status = 0
    try:
        safe_duration = round(max(0.0, float(duration_ms)), 2)
    except (TypeError, ValueError):
        safe_duration = 0.0
    return {
        "request_id": safe_id,
        "method": safe_method,
        "path": safe_path,
        "status": safe_status,
        "duration_ms": safe_duration,
    }
