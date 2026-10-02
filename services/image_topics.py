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
        oldest_key = min(_TOPIC_IMAGE_CACHE, key=lambda item: _TOPIC_IMAGE_CACHE[item][0])
        _TOPIC_IMAGE_CACHE.pop(oldest_key, None)
    _TOPIC_IMAGE_CACHE[key] = (time.monotonic(), [dict(photo) for photo in photos])


def _contains_normalized_term(text: object, candidate: object, normalize: Callable[[object], str]) -> bool:
    normalized_candidate = normalize(candidate).strip()
    if not normalized_candidate:
        return False
    normalized_text = normalize(text)
    pattern = r"(?<!\w)" + re.escape(normalized_candidate) + r"(?!\w)"
    return re.search(pattern, normalized_text, flags=re.UNICODE) is not None


def knowledge_image_titles(
    message: object,
    knowledge: Mapping[str, object],
    *,
    normalize: Callable[[object], str],
    limit: int = 4,
) -> list[str]:
    text_value = normalize(message)
    titles: list[str] = []

    for region in knowledge.get("regions", []) or []:
        if not isinstance(region, Mapping):
            continue
        candidates = [
            region.get("name", ""),
            *(region.get("places", []) or []),
            *(region.get("highlights", []) or []),
            *(region.get("image_queries", []) or []),
        ]
        if any(_contains_normalized_term(text_value, candidate, normalize) for candidate in candidates):
            for candidate in candidates:
                if candidate and str(candidate) not in titles:
                    titles.append(str(candidate))
                    if len(titles) >= limit:
                        return titles

    for place in knowledge.get("places", []) or []:
        if not isinstance(place, Mapping):
            continue
        candidates = [place.get("name", ""), *(place.get("image_queries", []) or [])]
        if any(normalize(candidate) and normalize(candidate) in text_value for candidate in candidates):
            for candidate in candidates:
                if candidate and str(candidate) not in titles:
                    titles.append(str(candidate))
                    if len(titles) >= limit:
                        return titles
    return titles


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
        if any(alias and alias in text_value for alias in aliases):
            specific_titles.extend(
                str(query)
                for query in (place.get("image_queries") or [])
                if query
            )

    titles = (
        specific_titles
        if specific_titles
        else (knowledge_image_titles(message, 4) if knowledge_image_titles else globals()["knowledge_image_titles"](message, knowledge, normalize=normalize, limit=4))
        + list(topic_wikipedia_titles(message, 4))
    )
    if not titles:
        titles = ["Dakar Sénégal"]

    photos: list[dict] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()

    # Google Images is the primary provider for chat visual requests. One
    # focused query is enough to return a larger, faster gallery without
    # multiplying outbound image-search calls.
    primary_title = next((str(title or "").strip() for title in titles if str(title or "").strip()), "Dakar Sénégal")
    cache_key = (normalize(primary_title), max_photos, id(fetch_google_images), id(fetch_commons_images), id(fetch_city_image))
    cached = _cached_topic_images(cache_key)
    if cached is not None:
        return cached
    if fetch_google_images:
        try:
            candidates = fetch_google_images(primary_title, limit=max_photos)
        except Exception:
            logger.exception("Erreur recherche Google Images pour %s", primary_title)
            candidates = []
        for photo in candidates:
            if not photo:
                continue
            photo["search_query"] = primary_title
            src = photo.get("url", "")
            if not src or src in seen_urls:
                continue
            seen_urls.add(src)
            photos.append(photo)
            if len(photos) >= max_photos:
                _store_topic_images(cache_key, photos)
                return [dict(photo) for photo in photos]

    # Wikimedia remains a relevance-oriented fallback when Google returns too
    # few results or is temporarily unavailable.
    for title in titles:
        title = str(title or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        try:
            candidates = fetch_commons_images(title, limit=min(4, max_photos - len(photos)))
        except Exception:
            logger.exception("Erreur recherche photos Commons pour %s", title)
            candidates = []
        if not candidates and len(photos) == 0:
            try:
                fallback = fetch_city_image(title)
                candidates = [fallback] if fallback else []
            except Exception:
                logger.exception("Erreur fallback photo pour %s", title)
                candidates = []
        for photo in candidates:
            if not photo:
                continue
            photo["search_query"] = title
            photo["display_url"] = image_proxy_url(photo.get("url", ""))
            src = photo.get("url", "")
            if not src or src in seen_urls:
                continue
            seen_urls.add(src)
            photos.append(photo)
            if len(photos) >= max_photos:
                _store_topic_images(cache_key, photos)
                return [dict(photo) for photo in photos]

    if photos:
        _store_topic_images(cache_key, photos)
        return [dict(photo) for photo in photos]
    return None
