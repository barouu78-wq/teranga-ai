"""Services de recherche d'images pour Teranga AI."""

import json
import logging
import re
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)
_IMAGE_CACHE = {}


def fetch_google_images(query, api_key, cse_id, limit=4, urlopen_fn=None):
    """Recherche d'images via Google Custom Search JSON API."""
    query = str(query or "").strip()
    api_key = str(api_key or "").strip()
    cse_id = str(cse_id or "").strip()
    if not query or not api_key or not cse_id:
        return []

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "searchType": "image",
        "num": str(min(max(int(limit), 1), 10)),
        "safe": "active",
        "gl": "sn",
        "imgType": "photo",
    }
    req = Request(
        "https://www.googleapis.com/customsearch/v1?" + urlencode(params),
        headers={"User-Agent": "TerangaAI/1.0 (Google Images)"},
    )
    opener = urlopen_fn or urlopen
    try:
        with opener(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        safe_body = body.replace(api_key, "[REDACTED]") if api_key else body
        logger.error("Google Custom Search HTTP %s pour %r (cx=%s): %s", exc.code, query, cse_id, safe_body[:1200])
        raise

    out, seen = [], set()
    for item in data.get("items", []) or []:
        image = item.get("image") or {}
        thumbnail = image.get("thumbnailLink") or ""
        original = image.get("url") or item.get("link") or ""
        context = image.get("contextLink") or item.get("link") or ""
        if not thumbnail or not original or not context:
            continue
        if not thumbnail.startswith(("https://", "http://")):
            continue
        key = thumbnail.split("?", 1)[0].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "url": original,
            "display_url": thumbnail,
            "alt": str(item.get("title") or query)[:160],
            "credit": "Google Images",
            "page_url": context,
        })
        if len(out) >= limit:
            break
    return out


def fetch_commons_images(title, limit=4, image_validator=None, display_url_builder=None, urlopen_fn=None):
    query = str(title or "").strip()
    if not query:
        return []
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(min(max(limit * 3, 6), 20)),
        "prop": "imageinfo",
        "iiprop": "url|mime|thumbmime|extmetadata",
        "iiurlwidth": "960",
        "origin": "*",
    }
    req = Request(
        "https://commons.wikimedia.org/w/api.php?" + urlencode(params),
        headers={"User-Agent": "TerangaAI/1.0 (image lookup)"},
    )
    opener = urlopen_fn or urlopen
    with opener(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    validate = image_validator or (lambda src: str(src or ""))
    out, seen = [], set()
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = str(info.get("mime") or "").lower()
        thumb_mime = str(info.get("thumbmime") or "").lower()
        if mime and not mime.startswith("image/"):
            continue
        if thumb_mime and not thumb_mime.startswith("image/"):
            continue
        src = validate(info.get("url") or info.get("thumburl"))
        if not src or src in seen:
            continue
        meta = info.get("extmetadata") or {}

        def meta_text(key):
            value = meta.get(key, {})
            return re.sub(r"<[^>]+>", "", value.get("value", "")).strip() if isinstance(value, dict) else ""

        item = {
            "url": src,
            "display_url": display_url_builder(src) if display_url_builder else src,
            "alt": meta_text("ImageDescription") or page.get("title", query),
            "credit": "Wikimédia Commons",
            "artist": meta_text("Artist"),
            "license": meta_text("LicenseShortName"),
            "page_url": "https://commons.wikimedia.org/wiki/" + quote(page.get("title", ""), safe=":"),
        }
        out.append(item)
        seen.add(src)
        if len(out) >= limit:
            break
    return out


def fetch_commons_image(title, image_validator=None, display_url_builder=None, urlopen_fn=None):
    images = fetch_commons_images(title, limit=1, image_validator=image_validator, display_url_builder=display_url_builder, urlopen_fn=urlopen_fn)
    return images[0] if images else None


def fetch_city_image(title, wiki_summary_fn, image_validator, sanitize_text_fn):
    if not title:
        return None
    if title in _IMAGE_CACHE:
        return _IMAGE_CACHE[title]
    english = title.replace(" (Sénégal)", "").replace(" (Senegal)", "")
    found = None
    for lang, page in (("fr", title), ("en", english)):
        try:
            data = wiki_summary_fn(lang, page)
        except Exception:
            continue
        src = image_validator((data.get("thumbnail") or {}).get("source") or "")
        if not src:
            src = image_validator((data.get("originalimage") or {}).get("source") or "")
        if not src:
            continue
        found = {
            "url": src,
            "alt": sanitize_text_fn(data.get("title") or title, 80),
            "credit": "Wikimédia",
        }
        break
    if not found:
        try:
            found = fetch_commons_image(title, image_validator=image_validator)
        except Exception:
            logger.exception("Erreur recherche Wikimedia Commons pour %s", title)
    _IMAGE_CACHE[title] = found
    return found
