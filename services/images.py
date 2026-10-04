"""Services de recherche d'images pour Teranga AI."""

import json
import logging
import re
import unicodedata
import time

from .photo_search import normalize_place_query, relevant_image_evidence
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


logger = logging.getLogger(__name__)
_IMAGE_CACHE = {}
_IMAGE_CACHE_TTL_SECONDS = 900
_IMAGE_CACHE_MAX_ENTRIES = 128
_COMMONS_CACHE: dict[tuple[str, int, int, int, int], tuple[float, list[dict]]] = {}
_COMMONS_CACHE_TTL_SECONDS = 300
_COMMONS_CACHE_MAX_ENTRIES = 128


def _normalize(value):
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _photo_matches_query(query, page_title, description):
    """Reject obvious off-topic Commons results for precise place searches."""
    q = _normalize(query)
    evidence = _normalize(f"{page_title} {description}")

    # Strict matching for places where a generic regional result is especially
    # misleading. The query can contain accents, typos, or "ile de".
    precise_aliases = {
        "goree": ("goree", "ile de goree", "goree island"),
        "ile de goree": ("goree", "goree island"),
        "lac rose": ("lac rose", "lake retba", "retba"),
        "joal-fadiouth": ("joal", "fadiouth"),
        "fadiouth": ("fadiouth", "joal"),
        "cap skirring": ("cap skirring",),
    }
    for key, aliases in precise_aliases.items():
        if key in q:
            return any(alias in evidence for alias in aliases)

    return True


def _google_photo_matches_query(query, alt, page_url):
    """Reject obvious off-topic city results from Google Images."""
    q = _normalize(query)
    evidence = _normalize(f"{alt} {page_url}")
    strict_exclusions = {
        "dakar": ("saly", "saly portudal", "mbour", "somone", "popenguine"),
        "saly": ("dakar", "saint louis", "thies"),
    }
    for city, excluded in strict_exclusions.items():
        if _contains_text_term(q, city):
            if any(_contains_text_term(evidence, term) for term in excluded):
                return False
    return True


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
        message = "Google Custom Search HTTP %s pour %r (cx=%s): %s" % (exc.code, query, cse_id, safe_body[:1200])
        logger.error(message)
        print(message, flush=True)
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
        alt = str(item.get("title") or query)[:160]
        if not _google_photo_matches_query(query, alt, context):
            continue
        out.append({
            "url": original,
            "display_url": thumbnail,
            "alt": alt,
            "credit": "Google Images",
            "page_url": context,
        })
        if len(out) >= limit:
            break
    return [dict(item) for item in out]


def fetch_commons_images(title, limit=4, image_validator=None, display_url_builder=None, urlopen_fn=None):
    query = normalize_place_query(title)
    if not query:
        return []
    cache_key = (
        _normalize(query),
        int(limit),
        id(image_validator),
        id(display_url_builder),
        id(urlopen_fn),
    )
    cached = _COMMONS_CACHE.get(cache_key)
    if cached is not None:
        cached_at, cached_value = cached
        if time.monotonic() - cached_at < _COMMONS_CACHE_TTL_SECONDS:
            return [dict(item) for item in cached_value]
        _COMMONS_CACHE.pop(cache_key, None)
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(min(max(limit * 4, 8), 30)),
        "prop": "imageinfo",
        "iiprop": "url|mime|thumbmime|extmetadata",
        "iiurlwidth": "1280",
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
        meta = info.get("extmetadata") or {}

        def meta_text(key):
            value = meta.get(key, {})
            return re.sub(r"<[^>]+>", "", value.get("value", "")).strip() if isinstance(value, dict) else ""

        description = meta_text("ImageDescription")
        page_title = page.get("title", query)
        if not _photo_matches_query(query, page_title, description) or not relevant_image_evidence(query, page_title, description):
            continue

        src = validate(info.get("thumburl") or info.get("url"))
        if not src or src in seen:
            continue

        item = {
            "url": src,
            "display_url": display_url_builder(src) if display_url_builder else src,
            "alt": description or page_title,
            "credit": "Wikimédia Commons",
            "artist": meta_text("Artist"),
            "license": meta_text("LicenseShortName"),
            "page_url": "https://commons.wikimedia.org/wiki/" + quote(page_title, safe=":"),
        }
        out.append(item)
        seen.add(src)
        if len(out) >= limit:
            break
    if len(_COMMONS_CACHE) >= _COMMONS_CACHE_MAX_ENTRIES and cache_key not in _COMMONS_CACHE:
        oldest = min(_COMMONS_CACHE, key=lambda key: _COMMONS_CACHE[key][0])
        _COMMONS_CACHE.pop(oldest, None)
    _COMMONS_CACHE[cache_key] = (time.monotonic(), [dict(item) for item in out])
    return [dict(item) for item in out]


def fetch_commons_image(title, image_validator=None, display_url_builder=None, urlopen_fn=None):
    images = fetch_commons_images(title, limit=1, image_validator=image_validator, display_url_builder=display_url_builder, urlopen_fn=urlopen_fn)
    return images[0] if images else None


def fetch_city_image(title, wiki_summary_fn, image_validator, sanitize_text_fn):
    if not title:
        return None
    cached = _IMAGE_CACHE.get(title)
    if cached is not None:
        cached_at, cached_value = cached
        if time.monotonic() - cached_at < _IMAGE_CACHE_TTL_SECONDS:
            return cached_value
        _IMAGE_CACHE.pop(title, None)
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
    if len(_IMAGE_CACHE) >= _IMAGE_CACHE_MAX_ENTRIES:
        oldest = min(_IMAGE_CACHE, key=lambda key: _IMAGE_CACHE[key][0])
        _IMAGE_CACHE.pop(oldest, None)
    _IMAGE_CACHE[title] = (time.monotonic(), found)
    return found



PHOTO_TOPICS = (
    ("monument de la renaissance", "Monument de la Renaissance africaine"),
    ("renaissance africaine", "Monument de la Renaissance africaine"),
    ("maison des esclaves", "Maison des Esclaves"),
    ("cap skirring", "Cap Skirring"),
    ("île de gorée", "Île de Gorée"), ("ile de goree", "Île de Gorée"),
    ("saint-louis", "Saint-Louis (Sénégal)"), ("saint louis", "Saint-Louis (Sénégal)"),
    ("niokolo-koba", "Parc national du Niokolo-Koba"), ("niokolo koba", "Parc national du Niokolo-Koba"),
    ("djoudj", "Parc national des oiseaux du Djoudj"), ("joal-fadiouth", "Joal-Fadiouth"),
    ("fadiouth", "Joal-Fadiouth"), ("joal", "Joal-Fadiouth"),
    ("thiéboudienne", "Thiéboudienne"), ("thieboudienne", "Thiéboudienne"),
    ("ceebu jen", "Thiéboudienne"), ("ceebu jën", "Thiéboudienne"),
    ("café touba", "Café Touba"), ("cafe touba", "Café Touba"),
    ("lac rose", "Lac Retba"), ("lac retba", "Lac Retba"),
    ("richard-toll", "Richard-Toll"), ("richard toll", "Richard-Toll"),
    ("grande mosquée de touba", "Grande Mosquée de Touba"), ("mosquée de touba", "Grande Mosquée de Touba"),
    ("casamance", "Casamance"), ("somone", "La Somone"), ("yassa", "Yassa"), ("bissap", "Bissap"),
    ("mafé", "Mafé"), ("maafe", "Mafé"), ("diamniadio", "Diamniadio"),
    ("guédiawaye", "Guédiawaye"), ("guediawaye", "Guédiawaye"), ("tambacounda", "Tambacounda"),
    ("ziguinchor", "Ziguinchor"), ("kedougou", "Kédougou"), ("kédougou", "Kédougou"),
    ("kaffrine", "Kaffrine"), ("sédhiou", "Sédhiou"), ("sedhiou", "Sédhiou"),
    ("rufisque", "Rufisque"), ("kaolack", "Kaolack"), ("diourbel", "Diourbel"),
    ("gorée", "Île de Gorée"), ("goree", "Île de Gorée"), ("mbour", "M'Bour"), ("m'bour", "M'Bour"),
    ("touba", "Touba (Sénégal)"), ("thiès", "Thiès"), ("thies", "Thiès"), ("kolda", "Kolda"),
    ("matam", "Matam"), ("louga", "Louga"), ("fatick", "Fatick"), ("podor", "Podor"),
    ("saly", "Saly Portudal"), ("pikine", "Pikine"), ("dakar", "Dakar"), ("ndar", "Saint-Louis (Sénégal)"),
)


def _contains_text_term(text: object, term: object) -> bool:
    normalized_text = _normalize(text)
    normalized_term = _normalize(term).strip()
    if not normalized_term:
        return False
    pattern = r"(?<!\w)" + re.escape(normalized_term) + r"(?!\w)"
    return re.search(pattern, normalized_text, flags=re.UNICODE) is not None


def topic_wikipedia_titles(message: object, limit: int = 2) -> list[str]:
    found, seen = [], set()
    for key, title in PHOTO_TOPICS:
        if _contains_text_term(message, key) and title not in seen:
            seen.add(title)
            found.append(title)
            if len(found) >= limit:
                break
    return found


def wiki_summary(lang: str, title: str) -> dict:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + quote(title)
    req = Request(url, headers={"User-Agent": "TerangaAI/1.0 (https://teranga-ai-1.onrender.com)"})
    with urlopen(req, timeout=2) as resp:
        return json.loads(resp.read().decode("utf-8"))

ALLOWED_IMAGE_HOSTS = {"upload.wikimedia.org", "thumb.wikimedia.org"}

def usable_wiki_image(src: object) -> str:
    src = str(src or "").split("?", 1)[0][:2000]
    if not src.startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/")):
        return ""
    lowered = src.lower()
    if "flag_of" in lowered or "coat_of_arms" in lowered or lowered.endswith(".svg.png"):
        return ""
    return src


def image_proxy_url(src: object) -> str:
    src = usable_wiki_image(src)
    return f"/image-proxy?url={quote(src, safe='')}" if src else ""


def allowed_image_url(src: object) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(str(src or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    return bool(parsed.scheme == "https" and host in ALLOWED_IMAGE_HOSTS and not parsed.username and not parsed.password and parsed.port in (None, 443))

class SafeImageRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_image_url(newurl):
            raise ValueError("Redirection image non autorisée")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def safe_image_fetch(src: object, max_bytes: int, timeout: float = 5.0, opener=None):
    if not allowed_image_url(src):
        raise ValueError("Source image non autorisée")
    req = Request(str(src), headers={"User-Agent": "TerangaAI/1.0"})
    image_opener = opener or build_opener(SafeImageRedirectHandler)
    with image_opener.open(req, timeout=timeout) as upstream:
        headers = getattr(upstream, "headers", {})
        get_type = getattr(headers, "get_content_type", None)
        content_type = get_type() if callable(get_type) else str(headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise ValueError("Type image invalide")
        length = str(headers.get("Content-Length") or "").strip()
        if length.isdigit() and int(length) > max_bytes:
            raise ValueError("Image trop volumineuse")
        data = upstream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Image trop volumineuse")
        return content_type, data


def should_fetch_images(message: object) -> bool:
    lowered = _normalize(message)
    explicit = (
        "photo", "photos", "image", "images", "visuel", "visuels",
        "montre moi", "montre-moi", "affiche", "fais voir",
        "a quoi ressemble", "a quoi ca ressemble", "voir le lieu",
        "voir la ville", "montre la ville", "show me", "show",
        "picture", "pictures",
    )
    return any(_contains_text_term(lowered, term) for term in explicit)
