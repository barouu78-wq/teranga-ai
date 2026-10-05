"""Topic image orchestration independent from Flask request handling."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence


_TOPIC_IMAGE_CACHE: dict[tuple[str, int, int, int, int], tuple[float, list[dict]]] = {}
_TOPIC_IMAGE_CACHE_TTL = 300.0
_TOPIC_IMAGE_CACHE_MAX = 128


def _cached_topic_images(key: tuple[str, int, int, int, int]) -> list[dict] | None:
    cached = _TOPIC_IMAGE_CACHE.get(key)
    if not cached:
        return None
    stored_at, photos = cached
    if time.monotonic() - stored_at >= _TOPIC_IMAGE_CACHE_TTL:
        _TOPIC_IMAGE_CACHE.pop(key, None)
        return None
    return [dict(photo) for photo in photos]


def _store_topic_images(key: tuple[str, int, int, int, int], photos: list[dict]) -> None:
    if len(_TOPIC_IMAGE_CACHE) >= _TOPIC_IMAGE_CACHE_MAX:
        oldest_key = min(list(_TOPIC_IMAGE_CACHE.items()), key=lambda entry: entry[1][0])[0]
        _TOPIC_IMAGE_CACHE.pop(oldest_key, None)
    _TOPIC_IMAGE_CACHE[key] = (time.monotonic(), [dict(photo) for photo in photos])


def _contains_normalized_term(text: object, candidate: object, normalize: Callable[[object], str]) -> bool:
    normalized_candidate = normalize(candidate).strip()
    if not normalized_candidate:
        return False
    normalized_text = normalize(text)
    pattern = r"(?<!\w)" + re.escape(normalized_candidate) + r"(?!\w)"
    return re.search(pattern, normalized_text, flags=re.UNICODE) is not None


_SHORT_NAME = re.compile(r"^.*?\b(?:de|du|des|d')\s+(?:la\s+|l')?(.+)$", re.IGNORECASE)


def _short_place_name(name: str) -> str:
    """« Île de Gorée » → « Gorée » ; « Parc national de la Langue de Barbarie » → « Langue de Barbarie »."""
    match = _SHORT_NAME.match(str(name or "").strip())
    short = match.group(1).strip() if match else ""
    return short if len(short) >= 4 else ""


def knowledge_image_titles(
    message: object,
    knowledge: Mapping[str, object],
    *,
    normalize: Callable[[object], str],
    limit: int = 4,
) -> list[str]:
    text_value = normalize(message)
    titles: list[str] = []

    def collect(candidates) -> bool:
        if any(_contains_normalized_term(text_value, candidate, normalize) for candidate in candidates):
            for candidate in candidates:
                if candidate and str(candidate) not in titles:
                    titles.append(str(candidate))
                    if len(titles) >= limit:
                        return True
        return False

    region_names = {
        normalize(region.get("name", ""))
        for region in knowledge.get("regions", []) or []
        if isinstance(region, Mapping)
    }

    # Le lieu précis passe avant sa région (« désert de Lompoul » avant « Louga »).
    # Le nom court (« Gorée » pour « Île de Gorée ») sert aussi à reconnaître le
    # lieu, mais seules ses requêtes d'images sont proposées.
    for place in knowledge.get("places", []) or []:
        if not isinstance(place, Mapping):
            continue
        name = str(place.get("name", ""))
        candidates = [name, *(place.get("image_queries", []) or [])]
        short = _short_place_name(name)
        if short and normalize(short) in region_names:
            # « Corniche de Dakar » ne doit pas capter toute demande sur Dakar.
            short = ""
        if (
            short
            and not any(_contains_normalized_term(text_value, c, normalize) for c in candidates)
            and _contains_normalized_term(text_value, short, normalize)
        ):
            candidates = [short, *(c for c in candidates if c)]
        if collect(candidates):
            return titles

    for region in knowledge.get("regions", []) or []:
        if isinstance(region, Mapping) and collect([
            region.get("name", ""),
            *(region.get("places", []) or []),
            *(region.get("highlights", []) or []),
            *(region.get("image_queries", []) or []),
        ]):
            return titles
    return titles


def _build_primary_query(
    message: object,
    specific_titles: Sequence[str],
    discovered_titles: Sequence[str],
    normalize: Callable[[object], str],
) -> str:
    """Build an image query from the actual request instead of a generic Dakar fallback."""
    specific = next((str(title).strip() for title in specific_titles if str(title).strip()), "")
    if specific:
        return specific

    discovered = next((str(title).strip() for title in discovered_titles if str(title).strip()), "")
    if discovered:
        return discovered

    raw = str(message or "").strip()
    normalized = normalize(raw)
    if not normalized:
        return "Sénégal"

    # Keep the user's visual intent while removing conversational filler.
    filler = (
        "montre moi", "montre-moi", "montre", "affiche", "affiche moi",
        "affiche-moi", "fais voir", "je veux voir", "donne moi", "donne-moi",
        "des photos de", "des photos du", "des photos d", "photo de", "photos de",
        "photo du", "photos du", "photo d", "photos d",
    )
    filler = filler + (
        "des photos", "des images de", "des images", "les photos de", "les photos",
        "photos", "photo", "images", "image", "stp", "s'il te plait", "svp",
    )
    query = raw
    # « montre moi des photos de plage » : on retire toutes les formules,
    # pas seulement la première (sinon « des photos de plage » partait à Google).
    changed = True
    while changed:
        changed = False
        for prefix in sorted(filler, key=len, reverse=True):
            if normalize(query).startswith(normalize(prefix) + " "):
                query = query[len(prefix):].strip(" :,-")
                changed = True
                break
    if not normalize(query):
        query = "Sénégal"
    if "senegal" not in normalize(query):
        query = f"{query} Sénégal"
    return query[:180]


# Recherches d'images en parallèle : la plus lente fixe la durée, pas la somme.
_PHOTO_POOL = None
PHOTO_SEARCH_BUDGET_SECONDS = 9.0


def _run_parallel(jobs, logger, budget=None):
    """{(source, titre): résultat} ; une source en erreur ou trop lente est ignorée."""
    global _PHOTO_POOL
    if not jobs:
        return {}
    if len(jobs) == 1:
        kind, title, call = jobs[0]
        try:
            return {(kind, title): call()}
        except Exception:
            logger.exception("Erreur recherche photos %s pour %s", kind, title)
            return {}
    from concurrent.futures import ThreadPoolExecutor, wait

    if _PHOTO_POOL is None:
        _PHOTO_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="photos")
    futures = {_PHOTO_POOL.submit(call): (kind, title) for kind, title, call in jobs}
    done, _pending = wait(futures, timeout=PHOTO_SEARCH_BUDGET_SECONDS if budget is None else budget)
    results = {}
    for future in done:
        kind, title = futures[future]
        try:
            results[(kind, title)] = future.result()
        except Exception:
            logger.exception("Erreur recherche photos %s pour %s", kind, title)
    return results


def fetch_topic_images(
    message: object,
    knowledge: Mapping[str, object],
    *,
    normalize: Callable[[object], str],
    should_fetch_images: Callable[[object], bool],
    topic_wikipedia_titles: Callable[[object, int], Sequence[str]],
    knowledge_image_titles: Callable[[object, int], Sequence[str]] | None = None,
    fetch_commons_images: Callable[..., list[dict]],
    fetch_google_images: Callable[..., list[dict]] | None = None,
    fetch_article_images: Callable[..., list[dict]] | None = None,
    fetch_city_image: Callable[[str], dict | None],
    image_proxy_url: Callable[[object], str],
    logger,
    max_photos: int = 8,
) -> list[dict] | None:
    text_value = normalize(message)
    if not should_fetch_images(message):
        return None

    specific_titles: list[str] = []
    for place in knowledge.get("places", []) or []:
        if not isinstance(place, Mapping):
            continue
        name = normalize(str(place.get("name", "")))
        aliases = [name]
        if name.startswith("ile de "):
            aliases.append(name[7:])
            if name == "ile de goree":
                aliases.append("gore")
        if name.startswith("île de "):
            aliases.append(name[7:])
        if any(_contains_normalized_term(text_value, alias, normalize) for alias in aliases):
            image_queries = [str(query) for query in (place.get("image_queries") or []) if query]
            # A recognized place must remain specific even when its optional
            # image_queries metadata is empty. This also handles short aliases
            # such as "gore" for Île de Gorée without falling back to Dakar.
            specific_titles.extend(image_queries or [str(place.get("name", "")).strip()])

    # Keep a few high-value Senegal place aliases resilient even when
    # structured knowledge is incomplete. These are search hints, not a
    # replacement for the knowledge base.
    normalized_message = normalize(message)
    if _contains_normalized_term(normalized_message, "gore", normalize) or _contains_normalized_term(normalized_message, "goree", normalize):
        specific_titles.append("Île de Gorée")

    if specific_titles:
        discovered_titles = []
    else:
        discovered_titles = (
            knowledge_image_titles(message, 4)
            if knowledge_image_titles
            else globals()["knowledge_image_titles"](message, knowledge, normalize=normalize, limit=4)
        )
        discovered_titles = list(discovered_titles) + list(topic_wikipedia_titles(message, 4))

    primary_title = _build_primary_query(message, specific_titles, discovered_titles, normalize)
    titles = list(specific_titles or discovered_titles or [primary_title])

    photos: list[dict] = []
    seen_urls: set[str] = set()

    # Cache by the actual visual request so different requests do not reuse
    # the same generic Dakar gallery.
    cache_key = (
        normalize(primary_title),
        max_photos,
        id(fetch_google_images),
        id(fetch_article_images),
        id(fetch_commons_images),
        id(fetch_city_image),
    )
    cached = _cached_topic_images(cache_key)
    if cached is not None:
        return cached

    def add(candidates, query, proxied):
        for photo in candidates or []:
            src = (photo or {}).get("url", "")
            if not src or src in seen_urls or len(photos) >= max_photos:
                continue
            photo["search_query"] = query
            if proxied:
                photo["display_url"] = image_proxy_url(src)
            seen_urls.add(src)
            photos.append(photo)

    def finish():
        if photos:
            _store_topic_images(cache_key, photos)
            return [dict(photo) for photo in photos]
        return None

    # Étape 1, en parallèle : Google et les photos des articles Wikipédia des
    # lieux reconnus (choisies par des rédacteurs ; jamais pour une requête
    # libre comme « plage », dont l'article montrerait le monde entier).
    article_titles = [str(t or "").strip() for t in list(specific_titles or discovered_titles)[:2]]
    article_titles = [t for t in dict.fromkeys(article_titles) if t] if fetch_article_images else []
    jobs = []
    if fetch_google_images:
        jobs.append(("google", primary_title, lambda: fetch_google_images(primary_title, limit=max_photos)))
    for title in article_titles:
        jobs.append(("article", title, lambda title=title: fetch_article_images(title, limit=max_photos)))
    results = _run_parallel(jobs, logger)
    add(results.get(("google", primary_title)), primary_title, proxied=False)
    for title in article_titles:
        add(results.get(("article", title)), title, proxied=True)
    if len(photos) >= 4:
        return finish()

    # Étape 2 (seulement s'il manque des photos) : recherche Commons, en
    # parallèle sur les premiers titres.
    commons_titles = [t for t in dict.fromkeys(str(t or "").strip() for t in titles) if t][:4]
    jobs = [("commons", t, lambda t=t: fetch_commons_images(t, limit=4)) for t in commons_titles]
    results = _run_parallel(jobs, logger)
    for title in commons_titles:
        add(results.get(("commons", title)), title, proxied=True)
    for title in commons_titles:
        if photos:
            break
        try:
            fallback = fetch_city_image(title)
        except Exception:
            logger.exception("Erreur fallback photo pour %s", title)
            fallback = None
        add([fallback] if fallback else [], title, proxied=True)
    return finish()
