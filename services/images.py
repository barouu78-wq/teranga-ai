"""Services de recherche d'images pour Teranga AI."""

import json
import logging
import os
import re
import unicodedata
import time

from .photo_search import normalize_place_query, relevant_image_evidence
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


logger = logging.getLogger(__name__)


def wikimedia_user_agent() -> str:
    """User-Agent conforme à la politique Wikimédia (nom, version, contact).

    Wikimédia refuse (HTTP 403) les agents génériques venant d'hébergeurs
    cloud comme Render : sans cette identité, Wikipédia et Commons ne
    renvoient plus aucune photo.
    """
    contact = os.getenv("CONTACT_EMAIL", "").strip()
    contact = f"; {contact}" if re.fullmatch(r"[^@\s;()]+@[^@\s;()]+\.[A-Za-z]{2,}", contact) else ""
    return f"TerangaAI/1.0 (https://teranga-ai.fr/{contact}) Python-urllib"


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


def _google_photo_relevance_score(query, alt, page_url):
    """Score Google Images evidence so precise place requests rank first."""
    q = _normalize(query)
    evidence = _normalize(f"{alt} {page_url}")

    # Generic visual requests should stay broad: "plage Sénégal" may legitimately
    # return Saly, Dakar, Somone, etc. Precision is activated only when the query
    # contains a recognizable place.
    place_aliases = {
        "dakar": ("dakar",),
        "saly": ("saly", "saly portudal"),
        "mbour": ("mbour", "m'bour"),
        "somone": ("somone", "la somone"),
        "popenguine": ("popenguine",),
        "goree": ("goree", "ile de goree", "goree island"),
        "ile de goree": ("goree", "ile de goree", "goree island"),
        "saint louis": ("saint louis", "saint-louis"),
        "thies": ("thies",),
        "rufisque": ("rufisque",),
        "ziguinchor": ("ziguinchor",),
        "touba": ("touba",),
        "kaolack": ("kaolack",),
        "kedougou": ("kedougou",),
        "cap skirring": ("cap skirring",),
        "lac rose": ("lac rose", "lake retba", "retba"),
        "joal": ("joal", "fadiouth"),
        "fadiouth": ("fadiouth", "joal"),
    }

    matched_place = None
    for place, aliases in place_aliases.items():
        if any(_contains_text_term(q, alias) for alias in aliases):
            matched_place = place
            break

    score = 0
    if matched_place:
        aliases = place_aliases[matched_place]
        if any(_contains_text_term(evidence, alias) for alias in aliases):
            score += 100
        else:
            # A precise place was requested but the result provides no evidence
            # for it. Keep it only as a lower-ranked candidate.
            score -= 25

        # A different Senegalese city in the evidence is a strong contradiction
        # for a precise city request.
        other_places = {
            "dakar": ("saly", "mbour", "somone", "popenguine", "saint louis", "thies"),
            "saly": ("dakar", "mbour", "somone", "saint louis", "thies"),
            "mbour": ("dakar", "saly", "somone", "saint louis", "thies"),
            "somone": ("dakar", "saly", "mbour", "popenguine", "saint louis"),
            "popenguine": ("dakar", "saly", "mbour", "somone"),
            "saint louis": ("dakar", "saly", "mbour", "thies"),
            "thies": ("dakar", "saly", "mbour", "saint louis"),
        }
        for other in other_places.get(matched_place, ()):
            if _contains_text_term(evidence, other):
                score -= 120

    # Reward meaningful query words appearing in the title/source. This helps
    # rank "Monument de la Renaissance à Dakar" above generic Senegal results.
    stopwords = {
        "photo", "photos", "image", "images", "nataal", "montre", "moi", "de", "du", "des",
        "la", "le", "les", "a", "au", "aux", "en", "pour", "voir", "senegal",
    }
    tokens = [
        token for token in re.findall(r"[a-z0-9]+", q)
        if len(token) >= 3 and token not in stopwords
    ]
    for token in tokens:
        if _contains_text_term(evidence, token):
            score += 8

    return score


def _google_photo_matches_query(query, alt, page_url):
    """Reject only clearly contradictory Google Images results."""
    q = _normalize(query)
    evidence = _normalize(f"{alt} {page_url}")
    strict_exclusions = {
        "dakar": ("saly", "saly portudal", "mbour", "somone", "popenguine"),
        "saly": ("dakar", "saint louis", "thies"),
    }
    for city, excluded in strict_exclusions.items():
        if _contains_text_term(q, city) and any(
            _contains_text_term(evidence, term) for term in excluded
        ):
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
        "num": str(min(max(int(limit) * 3, 6), 10)),
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

    candidates, seen = [], set()
    for position, item in enumerate(data.get("items", []) or []):
        image = item.get("image") or {}
        thumbnail = image.get("thumbnailLink") or ""
        original = image.get("url") or item.get("link") or ""
        context = image.get("contextLink") or item.get("link") or ""
        if not thumbnail or not original or not context:
            continue
        if not thumbnail.startswith("https://"):
            continue
        if not str(context).startswith(("https://", "http://")):
            continue
        key = thumbnail.split("?", 1)[0].lower()
        if key in seen:
            continue
        seen.add(key)
        alt = str(item.get("title") or query)[:160]
        if not _google_photo_matches_query(query, alt, context):
            continue
        score = _google_photo_relevance_score(query, alt, context)
        # Score négatif : lieu précis demandé (Dakar…) mais absent du titre et
        # de la page source, ou autre ville citée. Mieux vaut moins de photos
        # (Wikipédia complète) qu'une photo d'ailleurs.
        if score < 0:
            continue
        candidates.append({
            "url": original,
            "display_url": thumbnail,
            "alt": alt,
            "credit": "Google Images",
            "page_url": context,
            "_score": score,
            "_position": position,
        })

    # Stable ordering keeps Google's original ranking as the tie-breaker.
    candidates.sort(key=lambda item: (-item["_score"], item["_position"]))
    out = []
    for item in candidates[:limit]:
        item = dict(item)
        item.pop("_score", None)
        item.pop("_position", None)
        out.append(item)
    return out


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
        # Photos bitmap d'au moins 1000 px : écarte cartes SVG et vignettes.
        "gsrsearch": f"{query} filetype:bitmap filew:>999",
        "gsrnamespace": "6",
        "gsrlimit": str(min(max(limit * 4, 8), 30)),
        "prop": "imageinfo",
        "iiprop": "url|mime|thumbmime|extmetadata",
        "iiurlwidth": "1280",
        "origin": "*",
    }
    req = Request(
        "https://commons.wikimedia.org/w/api.php?" + urlencode(params),
        headers={"User-Agent": wikimedia_user_agent()},
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
        oldest = min(list(_COMMONS_CACHE.items()), key=lambda entry: entry[1][0])[0]
        _COMMONS_CACHE.pop(oldest, None)
    _COMMONS_CACHE[cache_key] = (time.monotonic(), [dict(item) for item in out])
    return [dict(item) for item in out]


# Fichiers d'article à écarter : cartes, drapeaux, logos, schémas…
_ARTICLE_IMAGE_EXCLUDED = (
    "carte", "map", "locator", "location", "localisation", "flag", "drapeau", "logo",
    "blason", "coat of arms", "coat_of_arms", "armoiries", "emblem", "embleme", "seal",
    "icon", "icone", "plan ", "diagram", "chart", "graph", "signature", "relief",
    "satellite", "population", "pictogram", "symbol", "stamp", "timbre", "banknote", "billet",
)
_ARTICLE_CACHE: dict[tuple[str, int], tuple[float, list[dict]]] = {}


def _article_title_candidates(title):
    """« Dakar Sénégal » → ["Dakar (Sénégal)", "Dakar"] : l'homonyme sénégalais d'abord."""
    base = re.sub(r"\s+s[ée]n[ée]gal$", "", str(title or "").strip(), flags=re.I).strip(" ,")
    if not base:
        return []
    return [f"{base} (Sénégal)", base]


def fetch_article_images(title, limit=6, image_validator=None, display_url_builder=None, urlopen_fn=None, lang="fr"):
    """Photos choisies par les rédacteurs de l'article Wikipédia du lieu.

    Bien plus fiables qu'une recherche plein texte sur Commons, qui renvoie
    n'importe quelle photo prise dans la ville (chantiers, déchets, ciel…).
    """
    candidates = _article_title_candidates(title)
    if not candidates:
        return []
    cache_key = (_normalize(candidates[-1]), int(limit))
    cached = _ARTICLE_CACHE.get(cache_key)
    if cached is not None and time.monotonic() - cached[0] < _IMAGE_CACHE_TTL_SECONDS:
        return [dict(item) for item in cached[1]]

    opener = urlopen_fn or urlopen
    validate = image_validator or (lambda src: str(src or ""))
    out = []
    failures = 0
    for article in candidates:
        params = {
            "action": "query",
            "format": "json",
            "titles": article,
            "redirects": "1",
            "generator": "images",
            "gimlimit": "50",
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
            "iiurlwidth": "1280",
        }
        req = Request(
            f"https://{lang}.wikipedia.org/w/api.php?" + urlencode(params),
            headers={"User-Agent": wikimedia_user_agent()},
        )
        # Un échec sur « X (Sénégal) » ne doit pas empêcher d'essayer « X ».
        try:
            with opener(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            failures += 1
            logger.warning("Wikipédia images %r : %s %s", article, type(exc).__name__, getattr(exc, "code", ""))
            continue
        pages = ((data.get("query") or {}).get("pages") or {}).values()
        seen = set()
        for page in sorted(pages, key=lambda item: str(item.get("title", ""))):
            info = (page.get("imageinfo") or [{}])[0]
            name = _normalize(page.get("title", "")).replace("_", " ")
            if str(info.get("mime") or "").lower() != "image/jpeg":
                continue
            if any(term in name for term in _ARTICLE_IMAGE_EXCLUDED):
                continue
            width, height = int(info.get("width") or 0), int(info.get("height") or 0)
            if width < 800 or height < 500 or not 0.6 <= width / max(height, 1) <= 2.4:
                continue
            src = validate(info.get("thumburl") or info.get("url"))
            if not src or src in seen:
                continue
            seen.add(src)
            meta = info.get("extmetadata") or {}

            def meta_text(key, meta=meta):
                value = meta.get(key, {})
                return re.sub(r"<[^>]+>", "", value.get("value", "")).strip() if isinstance(value, dict) else ""

            # « Fichier:… » (fr) → « File:… », l'espace de noms universel de Commons.
            file_title = "File:" + str(page.get("title", "")).split(":", 1)[-1]
            out.append({
                "url": src,
                "display_url": display_url_builder(src) if display_url_builder else src,
                "alt": (meta_text("ImageDescription") or file_title.split(":", 1)[-1].rsplit(".", 1)[0])[:300],
                "credit": "Wikimédia Commons",
                "artist": meta_text("Artist"),
                "license": meta_text("LicenseShortName"),
                "page_url": "https://commons.wikimedia.org/wiki/" + quote(file_title.replace(" ", "_"), safe=":"),
            })
            if len(out) >= limit:
                break
        if out:
            break
    if not out and failures:
        # Panne réseau : ne pas mémoriser un faux « aucune photo ».
        if failures == len(candidates):
            raise OSError("Wikipédia injoignable")
        return []
    if len(_ARTICLE_CACHE) >= _IMAGE_CACHE_MAX_ENTRIES and cache_key not in _ARTICLE_CACHE:
        _ARTICLE_CACHE.pop(min(list(_ARTICLE_CACHE.items()), key=lambda entry: entry[1][0])[0], None)
    _ARTICLE_CACHE[cache_key] = (time.monotonic(), [dict(item) for item in out])
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
    network_failed = False
    for lang, page in (("fr", title), ("en", english)):
        try:
            data = wiki_summary_fn(lang, page)
        except Exception:
            network_failed = True
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
            network_failed = True
            logger.exception("Erreur recherche Wikimedia Commons pour %s", title)
    # Une panne passagère (délai, 429) ne doit pas faire croire « pas de photo »
    # pendant 15 min : on ne garde en cache que les vraies réponses.
    if found is None and network_failed:
        return None
    if len(_IMAGE_CACHE) >= _IMAGE_CACHE_MAX_ENTRIES:
        oldest = min(list(_IMAGE_CACHE.items()), key=lambda entry: entry[1][0])[0]
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
    # La langue entre dans le nom d'hôte : seules « fr » et « en » sont permises.
    if lang not in ("fr", "en"):
        raise ValueError("Langue Wikipédia non prise en charge.")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + quote(title)
    req = Request(url, headers={"User-Agent": wikimedia_user_agent()})
    # Adresse https construite ici, langue vérifiée ci-dessus.
    with urlopen(req, timeout=2) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8"))

ALLOWED_IMAGE_HOSTS = {"upload.wikimedia.org", "thumb.wikimedia.org"}
# Formats matriciels uniquement : un SVG servi depuis notre origine pourrait
# embarquer du script actif.
ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif"})

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
    req = Request(str(src), headers={"User-Agent": wikimedia_user_agent()})
    image_opener = opener or build_opener(SafeImageRedirectHandler)
    with image_opener.open(req, timeout=timeout) as upstream:
        headers = getattr(upstream, "headers", {})
        get_type = getattr(headers, "get_content_type", None)
        content_type = get_type() if callable(get_type) else str(headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_IMAGE_TYPES:
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
        "picture", "pictures", "nataal",
    )
    return any(_contains_text_term(lowered, term) for term in explicit)
