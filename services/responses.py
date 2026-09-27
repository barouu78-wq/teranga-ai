"""Response parsing helpers for Teranga AI.

Keep provider response traversal and source extraction independent from Flask
route orchestration.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .validation import sanitize_text


def _field(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_sources(*objs):
    found = []
    seen = set()

    def add(url, title=""):
        url = sanitize_text(url, 400)
        if not url.startswith(("http://", "https://")):
            return
        key = url.split("#", 1)[0].rstrip("/").lower()
        if key in seen or len(found) >= 5:
            return
        seen.add(key)
        host = urlparse(url).netloc.replace("www.", "").lower()
        if not host or host.endswith("openai.com") or host in {"localhost"}:
            return
        title = sanitize_text(title, 72) or host or "Source"
        found.append({"title": title, "url": url})

    def walk(node, depth=0):
        if node is None or depth > 8 or len(found) >= 5:
            return
        if isinstance(node, (list, tuple)):
            for item in node[:40]:
                walk(item, depth + 1)
            return
        url = _field(node, "url")
        title = _field(node, "title") or _field(node, "name") or ""
        atype = str(_field(node, "type") or "")
        if url and (
            "citation" in atype
            or atype in {"url_citation", "source"}
            or str(url).startswith("http")
        ):
            add(str(url), str(title or ""))
        for key in (
            "annotations", "output", "content", "response", "citation",
            "citations", "sources", "results", "action", "item",
        ):
            child = _field(node, key)
            if child is not None:
                walk(child, depth + 1)
        if depth < 2:
            dump = getattr(node, "model_dump", None)
            if callable(dump):
                try:
                    walk(dump(), depth + 1)
                except Exception:
                    pass

    for obj in objs:
        walk(obj)
    return found


def event_delta(event):
    etype = getattr(event, "type", "") or ""
    if etype in {"response.output_text.delta", "response.text.delta"}:
        return getattr(event, "delta", "") or ""
    delta = getattr(event, "delta", None)
    if isinstance(delta, str) and etype.endswith(".delta"):
        return delta
    return ""
